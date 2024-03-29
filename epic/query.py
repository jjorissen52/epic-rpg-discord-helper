import datetime

from asgiref.sync import sync_to_async

from django.db.models import Q
from django.db import transaction

from .models import CoolDown, Profile, Guild, Hunt
from .types.classes import Enum


def _upsert_cooldowns(cooldowns):
    q = Q(id=-1)
    cooldown_dict = {}
    # search for existing and update if they already exist
    for cooldown in cooldowns:
        cooldown_dict[(cooldown.profile_id, cooldown.type)] = cooldown
        q |= Q(profile_id=cooldown.profile_id) & Q(type=cooldown.type)
    for cooldown in CoolDown.objects.filter(q):
        cooldown.after = cooldown_dict.pop((cooldown.profile_id, cooldown.type)).after
        cooldown.save()
    # save left over as new
    for cooldown in cooldown_dict.values():
        cooldown.save()


upsert_cooldowns = sync_to_async(_upsert_cooldowns)


# does not exist actions
DNE_ACTIONS = Enum(["NONE", "RAISE"])


@sync_to_async
def get_instance(model_class, on_dne=DNE_ACTIONS.NONE, defaults=None, **kwargs):
    if on_dne not in DNE_ACTIONS:
        raise ValueError(f"on_dne must be one of {DNE_ACTIONS}")
    if defaults:
        return model_class.objects.get_or_create(defaults=defaults, **kwargs)
    elif on_dne == DNE_ACTIONS.RAISE:
        return model_class.objects.get(**kwargs)
    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None


@sync_to_async
def update_instance(instance, **kwargs):
    for k, v in kwargs.items():
        setattr(instance, k, v)
    instance.save()
    return instance


@sync_to_async
def query_filter(model_class, **kwargs):
    return model_class.objects.filter(**kwargs)


def _bulk_delete(model_class, kwargs_list=None, **kwargs):
    if kwargs_list and kwargs:
        raise ValueError("bulk_delete accepts either a list of dicts or some kwargs to filter on")
    q = Q(id=-1)
    if kwargs_list:
        for _kwargs in kwargs_list:
            q |= Q(**_kwargs)
        return model_class.objects.filter(q).delete()
    if kwargs:
        return model_class.objects.filter(**kwargs).delete()


bulk_delete = sync_to_async(_bulk_delete)


@sync_to_async
@transaction.atomic
def get_cooldown_messages():
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    flavor_map = CoolDown.COOLDOWN_TEXT_MAP
    messages, cleanup = [], []
    # get cooldowns minus special cases

    for cd_type in set(c[0] for c in CoolDown.COOLDOWN_TYPE_CHOICES) - {"guild"}:
        for _id, channel, uid in (
            Profile.objects.command_type_enabled(cd_type)
            .filter(cooldown__after__lte=now, cooldown__type=cd_type)
            .exclude(banned=True)
            .values_list("cooldown__id", "channel", "uid")
        ):
            messages.append((f"<@{uid}> {flavor_map[cd_type]} (**{cd_type.title()}**)", channel))
            cleanup.append(_id)
    CoolDown.objects.filter(id__in=cleanup).delete()
    cleanup.clear()
    return messages


@sync_to_async
@transaction.atomic
def get_guild_cooldown_messages():
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    flavor_map = CoolDown.COOLDOWN_TEXT_MAP
    messages = []
    for channel, uid, raid_dibbs_name, raid_dibbs_uid, notify in Guild.objects.filter(
        after__lte=now, after__isnull=False
    ).values_list(
        "profile__channel", "profile__uid", "raid_dibbs__last_known_nickname", "raid_dibbs__uid", "profile__notify"
    ):
        if notify:
            if raid_dibbs_uid and uid != raid_dibbs_uid:
                messages.append((f"<@{uid}> {raid_dibbs_name} is doin' a guild raid!! (**Guild**)", channel))
            elif raid_dibbs_uid:
                messages.append((f"<@{uid}> {flavor_map['guild']} (**Guild**) [YOU HAVE DIBBS!!]", channel))
            else:
                messages.append((f"<@{uid}> {flavor_map['guild']} (**Guild**)", channel))
    Guild.objects.filter(after__lte=now).update(after=None)
    return messages


@sync_to_async
def set_guild_cd(profile, after=None):
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    after = now + CoolDown.get_cooldown("guild") if not after else after
    guild = Guild.objects.filter(profile__uid=profile.uid).first()
    if not guild:
        return
    raid_dibbs_id = None if guild.raid_dibbs_id == profile.uid else guild.raid_dibbs_id
    Guild.objects.filter(profile__uid=profile.uid).update(after=after, raid_dibbs_id=raid_dibbs_id)


def _set_guild_membership(guild_membership_dict):
    for guild_name, member_id_list in guild_membership_dict.items():
        guild, _ = Guild.objects.get_or_create(name=guild_name)
        Profile.objects.filter(uid__in=member_id_list).update(player_guild=guild)


set_guild_membership = sync_to_async(_set_guild_membership)


@transaction.atomic
def update_hunt_results(hunt_result, possible_userids):
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    expiration = now - datetime.timedelta(seconds=10)
    target, money, xp, loot = hunt_result
    # delete open hunts that have expired
    Hunt.objects.open_hunts(possible_userids).filter(created__lt=expiration).delete()
    if possible_userids:
        open_hunts = Hunt.objects.open_hunts(possible_userids)
        # just have to do best effort in the
        # case of nickname collision
        open_hunt = open_hunts.first()
        if open_hunt:
            open_hunt.update(target=target, money=money, xp=xp, loot=loot)

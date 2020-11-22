import datetime

from asgiref.sync import sync_to_async

from django.db.models import Q

from .models import CoolDown, Profile
from .utils import Enum


@sync_to_async
def upsert_cooldowns(cooldowns):
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


@sync_to_async
def bulk_delete(model_class, **kwargs):
    return model_class.objects.filter(**kwargs).delete()


@sync_to_async
def get_cooldown_messages():
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    results = []
    for cooldown_type, _ in CoolDown.COOLDOWN_TYPE_CHOICES:
        results.extend(
            Profile.objects.command_type_enabled(cooldown_type)
            .filter(cooldown__after__lte=now, cooldown__type=cooldown_type)
            .values_list("cooldown__id", "cooldown__type", "channel", "uid")
        )
    return results


@sync_to_async
def cleanup_old_cooldowns():
    return CoolDown.objects.filter(after__lt=datetime.datetime.now(tz=datetime.timezone.utc)).delete()

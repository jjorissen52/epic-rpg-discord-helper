import re
import datetime
from asgiref.sync import sync_to_async

from django.db import models
from django.db.models import Q

from .mixins import UpdateAble
from .utils import Enum, tokenize


class JoinCode(models.Model):
    code = models.CharField(max_length=256)
    claimed = models.BooleanField(default=False)

    def __str__(self):
        return self.code


class Server(models.Model):
    id = models.PositiveBigIntegerField(primary_key=True)
    name = models.CharField(max_length=250)
    code = models.OneToOneField(JoinCode, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}({self.id}) joined with {self.code}"


class Profile(UpdateAble, models.Model):
    # TODO: add last seen channel here
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    last_known_nickname = models.CharField(max_length=250)
    uid = models.CharField(max_length=50, primary_key=True)
    notify = models.BooleanField(default=False)
    daily = models.BooleanField(default=True)
    weekly = models.BooleanField(default=True)
    lootbox = models.BooleanField(default=True)
    vote = models.BooleanField(default=True)
    hunt = models.BooleanField(default=True)
    adventure = models.BooleanField(default=True)
    training = models.BooleanField(default=True)
    duel = models.BooleanField(default=True)
    quest = models.BooleanField(default=True)
    work = models.BooleanField(default=True)
    horse = models.BooleanField(default=True)
    arena = models.BooleanField(default=True)
    dungeon = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.last_known_nickname}({self.uid})"


class CoolDown(models.Model):
    class Meta:
        unique_together = ("profile", "type")

    time_regex = re.compile(
        r"\(\*\*(?P<days>\d{1}d)?\s*(?P<hours>\d{1,2}h)?\s*(?P<minutes>\d{1,2}m)?\s*(?P<seconds>\d{1,2}s)\*\*\)"
    )
    field_regex = re.compile(r":clock4: ~-~ \*\*`(?P<field_name>[^`]*)`\*\*")

    COOLDOWN_TYPE_CHOICES = (
        ("daily", "daily"),
        ("weekly", "weekly"),
        ("lootbox", "lootbox"),
        ("vote", "vote"),
        ("hunt", "hunt"),
        ("adventure", "adventure"),
        ("training", "training"),
        ("duel", "duel"),
        ("mine", "work"),  # call it mining because that's in the CD message
        ("horse", "horse"),
        ("arena", "arena"),
        ("dungeon", "dungeon"),
    )

    COOLDOWN_MAP = {
        "daily": datetime.timedelta(hours=24),
        "weekly": datetime.timedelta(days=7),
        "lootbox": datetime.timedelta(hours=3),
        "vote": datetime.timedelta(hours=12),
        "hunt": datetime.timedelta(seconds=60),
        "adventure": datetime.timedelta(minutes=60),
        "training": datetime.timedelta(minutes=15),
        "duel": datetime.timedelta(hours=2),
        "work": datetime.timedelta(minutes=5),
        "mine": datetime.timedelta(minutes=5),
        "horse": datetime.timedelta(hours=24),
        "arena": datetime.timedelta(hours=24),
        "dungeon": datetime.timedelta(hours=12),
    }

    COMMAND_RESOLUTION_MAP = {
        "daily": lambda x: "daily",
        "weekly": lambda x: "weekly",
        "buy": lambda x: "lootbox" if "lootbox" in x else None,
        "vote": lambda x: "vote",
        "hunt": lambda x: "hunt",
        "adv": lambda x: "adventure",
        "adventure": lambda x: "adventure",
        "tr": lambda x: "training",
        "training": lambda x: "training",
        "ultraining": lambda x: "training",
        "duel": lambda x: "duel",
        "mine": lambda x: "work",
        "pickaxe": lambda x: "work",
        "drill": lambda x: "work",
        "dynamite": lambda x: "work",
        "pickup": lambda x: "work",
        "ladder": lambda x: "work",
        "tractor": lambda x: "work",
        "greenhouse": lambda x: "work",
        "chop": lambda x: "work",
        "axe": lambda x: "work",
        "bowsaw": lambda x: "work",
        "chainsaw": lambda x: "work",
        "fish": lambda x: "work",
        "net": lambda x: "work",
        "boat": lambda x: "work",
        "bigboat": lambda x: "work",
        "horse": lambda x: "horse" if any([o == x for o in ["training", "breeding", "race"]]) else None,
        "arena": lambda x: "arena",
        "big": lambda x: "arena" if "arena" in x else None,
        "dungeon": lambda x: "dungeon",
        "miniboss": lambda x: "dungeon",
    }

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    type = models.CharField(choices=COOLDOWN_TYPE_CHOICES, max_length=10)
    after = models.DateTimeField()

    def __str__(self):
        return f"{self.profile} can {self.type} after {self.after}"

    @staticmethod
    def cd_from_command(cmd):
        resolved = None
        split = tokenize(cmd)
        if not split:
            return None, None
        # zero argument commands will just return whether or not the command matched
        if len(split) == 1:
            resolved = CoolDown.COMMAND_RESOLUTION_MAP.get(split[0], lambda x: None)(None)
        else:
            cmd, *args = split
            # mutli-arguments must be resolved in the basis of other args
            resolved = CoolDown.COMMAND_RESOLUTION_MAP.get(cmd, lambda x: None)(" ".join(args))
        if not resolved:
            return None, None
        return resolved, datetime.datetime.now(tz=datetime.timezone.utc) + CoolDown.COOLDOWN_MAP[resolved]

    @staticmethod
    def from_cd(profile, fields):
        start = datetime.datetime.now(tz=datetime.timezone.utc)
        cooldowns = []
        cd_types = set(c[0] for c in CoolDown.COOLDOWN_TYPE_CHOICES)
        for field in fields:
            field_matches = CoolDown.field_regex.findall(field)
            if field_matches:
                time_matches = CoolDown.time_regex.findall(field)
                for i, field_name in enumerate(field_matches):
                    time_delta_params = {
                        key: int(time_matches[i][j][:-1]) if time_matches[i][j] else 0
                        for j, key in enumerate(["days", "hours", "minutes", "seconds"])
                    }

                    for cd_type in cd_types:
                        if cd_type in field_name.lower():
                            cooldowns.append(
                                CoolDown(
                                    profile=profile, type=cd_type, after=start + datetime.timedelta(**time_delta_params)
                                )
                            )
                            cd_types.remove(cd_type)
                            break
        return cooldowns


@sync_to_async
def upsert_cooldowns(cooldowns):
    q = Q()
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
    return instance.save()


@sync_to_async
def query_filter(model_class, **kwargs):
    return model_class.objects.filter(**kwargs)


# @sync_to_async
# def send_cooldown_messages():
# Profile.objects.filter(server__active=True).filter(notify=True).filter(cooldown__after__lt=datetime.datetime.now()).values("cooldown__type", "server")

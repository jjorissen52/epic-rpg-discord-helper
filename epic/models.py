import re
import pytz
import datetime
import itertools

from django.db import models

from .mixins import UpdateAble
from .utils import tokenize
from .managers import ProfileManager


class JoinCode(models.Model):
    code = models.CharField(max_length=256)
    claimed = models.BooleanField(default=False)

    def claim(self):
        self.claimed = True
        self.save()

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
    TIMEZONE_CHOICES = tuple(zip(pytz.common_timezones, pytz.common_timezones))

    uid = models.CharField(max_length=50, primary_key=True)

    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    channel = models.PositiveBigIntegerField()
    last_known_nickname = models.CharField(max_length=250)
    timezone = models.CharField(
        choices=TIMEZONE_CHOICES, max_length=max(map(len, pytz.common_timezones)), default="America/Chicago"
    )

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

    objects = ProfileManager()

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
        ("daily", "Time for your daily! :sun_with_face:"),
        ("weekly", "Looks like it's that time of the week... :newspaper"),
        ("lootbox", "Lootbox! :moneybag:"),
        ("vote", "You can vote again. :ballot_box:"),
        ("hunt", "is on the hunt! :crossed_swords:"),
        ("adventure", "Let's go on an adventure! :woman_running:"),
        ("quest", "The townspeople need our help! "),
        ("training", "want to get buff? :man_lifting_weights:"),
        ("duel", "It's time to d-d-d-d-duel! :crossed_swords:"),
        ("work", "Get back to work. :pick:"),
        ("horse", "Pie-O-My! :horse_racing:"),
        ("arena", "Heeyyyy lets go hurt each other. :circus_tent:"),
        ("dungeon", "can you reach the next area? :exclamation:"),
    )
    COOLDOWN_TEXT_MAP = {c[0]: c[1] for c in COOLDOWN_TYPE_CHOICES}
    COOLDOWN_MAP = {
        "daily": datetime.timedelta(hours=24),
        "weekly": datetime.timedelta(days=7),
        "lootbox": datetime.timedelta(hours=3),
        "vote": datetime.timedelta(hours=12),
        "hunt": datetime.timedelta(seconds=60),
        "adventure": datetime.timedelta(minutes=60),
        "quest": datetime.timedelta(hours=6),
        "training": datetime.timedelta(minutes=15),
        "duel": datetime.timedelta(hours=2),
        "work": datetime.timedelta(minutes=5),
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
        "quest": lambda x: "quest",
        "epic": lambda x: "quest" if "quest" in x else None,
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
        tokens = tokenize(cmd)
        if not tokens:
            return None, None
        # zero argument commands will just return whether or not the command matched
        if len(tokens) == 1:
            resolved = CoolDown.COMMAND_RESOLUTION_MAP.get(tokens[0], lambda x: None)(None)
        else:
            cmd, *args = tokens
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
                    # special case
                    if "mine" in field_name.lower():
                        cooldowns.append(
                            CoolDown(
                                profile=profile, type="work", after=start + datetime.timedelta(**time_delta_params)
                            )
                        )
        return cooldowns

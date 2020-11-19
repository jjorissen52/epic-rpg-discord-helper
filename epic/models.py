import re
import datetime
from asgiref.sync import sync_to_async

from django.db import models
from django.db.models import Q

from .mixins import UpdateAble


class Profile(UpdateAble, models.Model):
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


@sync_to_async
def get_profile(uid):
    return Profile.objects.get(uid=uid)


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
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    type = models.CharField(choices=COOLDOWN_TYPE_CHOICES, max_length=10)
    after = models.DateTimeField()

    def __str__(self):
        return f"{self.type} after {self.after}"

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

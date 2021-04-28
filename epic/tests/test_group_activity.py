import json
from pathlib import Path

from django.test import TestCase

from epic.handlers.rpg import RPGHandler, CoolDownHandler
from epic.models import Server, Profile, GroupActivity, Invite, CoolDown
from epic.types import Namespace

FIXTURE_PATH = Path(__file__).parent / "fixtures"


class FakeClient:
    user = "Test Client User"
    users = None

    def __init__(self, users: dict):
        self.users = {int(key): Namespace.from_collection(user) for key, user in users.items()}

    def get_user(self, user_id: int):
        return self.users.get(int(user_id), None)


class TestGroupActivity(TestCase):
    data_dir = FIXTURE_PATH / "group_activities"

    def initiate_group_activity(self, fixture_name):
        with open(self.data_dir / f"initiate_{fixture_name}.json", "r") as r:
            idata = Namespace.from_collection(json.load(r))

        with open(self.data_dir / f"confirm_{fixture_name}.json", "r") as r:
            confirm_data = Namespace.from_collection(json.load(r))

        server = Server.objects.create(id=idata.author.guild.id, name=idata.author.guild.name)
        # initiator
        initiator_id = idata.author.id
        Profile.objects.create(
            uid=initiator_id, server=server, channel=idata.channel.id, last_known_nickname=idata.author.name
        )
        # friend
        friend_id = int(Profile.user_id_regex.match(idata.content.split(" ")[-1]).groups()[0])
        Profile.objects.create(uid=friend_id, server=server, channel=idata.channel.id, last_known_nickname="friend")

        discord_client = FakeClient(
            {
                initiator_id: {"last_known_nickname": idata.author.name, "server": server, "channel": idata.channel.id},
                friend_id: {"last_known_nickname": "friend", "server": server, "channel": idata.channel.id},
            }
        )
        return initiator_id, friend_id, discord_client, server, idata, confirm_data

    def test_arena(self):
        initiator_id, friend_id, discord_client, server, idata, confirm_data = self.initiate_group_activity("arena")

        handler = CoolDownHandler(discord_client, idata, server)
        handler.handle()
        group_activity = GroupActivity.objects.first()
        invite = Invite.objects.first()
        self.assertEqual(int(group_activity.initiator.uid), initiator_id)
        self.assertEqual(group_activity.initiator.last_known_nickname, idata.author.name)
        self.assertEqual(group_activity.type, "arena")
        self.assertEqual(invite.activity_id, group_activity.id)
        self.assertEqual(int(invite.profile_id), friend_id)

        self.assertEqual(CoolDown.objects.count(), 0)
        handler = RPGHandler(discord_client, confirm_data, server)
        handler.handle()
        self.assertEqual(CoolDown.objects.count(), 2)

    def test_duel(self):
        initiator_id, friend_id, discord_client, server, idata, confirm_data = self.initiate_group_activity("duel")

        handler = CoolDownHandler(discord_client, idata, server)
        handler.handle()
        group_activity = GroupActivity.objects.first()
        invite = Invite.objects.first()
        self.assertEqual(int(group_activity.initiator.uid), initiator_id)
        self.assertEqual(group_activity.initiator.last_known_nickname, idata.author.name)
        self.assertEqual(group_activity.type, "duel")
        self.assertEqual(invite.activity_id, group_activity.id)
        self.assertEqual(int(invite.profile_id), friend_id)

        self.assertEqual(CoolDown.objects.count(), 0)
        handler = RPGHandler(discord_client, confirm_data, server)
        handler.handle()
        self.assertEqual(CoolDown.objects.count(), 2)

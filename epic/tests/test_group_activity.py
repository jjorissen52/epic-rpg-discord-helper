from pathlib import Path

from django.test import TestCase

from epic.handlers.rpg import RPGHandler, CoolDownHandler
from epic.models import Server, Profile, GroupActivity, Invite, CoolDown
from epic.tests.util import FakeClient, FixtureLoader

FIXTURE_PATH = Path(__file__).parent / "fixtures"


class TestGroupActivity(FixtureLoader, TestCase):
    data_dir = FIXTURE_PATH / "group_activities"

    @staticmethod
    def initiate_group_activity(idata):
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
        return initiator_id, friend_id, discord_client, server

    def _test_group_activity(self, activity, variant=None):
        idata, confirm_data = self.unpack_activities(activity, variant)
        initiator_id, friend_id, discord_client, server = self.initiate_group_activity(idata)

        handler = CoolDownHandler(discord_client, idata, server)
        handler.handle()
        group_activity = GroupActivity.objects.first()
        invite = Invite.objects.first()
        self.assertEqual(int(group_activity.initiator.uid), initiator_id)
        self.assertEqual(group_activity.initiator.last_known_nickname, idata.author.name)
        self.assertEqual(group_activity.type, activity)
        self.assertEqual(invite.activity_id, group_activity.id)
        self.assertEqual(int(invite.profile_id), friend_id)

        self.assertEqual(CoolDown.objects.count(), 0)
        handler = RPGHandler(discord_client, confirm_data, server)
        handler.handle()
        self.assertEqual(CoolDown.objects.count(), 2)

    def test_arena(self):
        self._test_group_activity("arena")

    def test_duel(self):
        self._test_group_activity("duel")

    def test_horse_breed(self):
        self._test_group_activity("horse", "breed")

    def test_horse_breeding(self):
        self._test_group_activity("horse", "breeding")

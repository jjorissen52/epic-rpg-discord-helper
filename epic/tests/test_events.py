import unittest
from pathlib import Path

from django.test import TestCase

from epic.handlers.rpg import CoolDownHandler, RPGHandler
from epic.models import Server, Profile, CoolDown
from epic.tests.util import FixtureLoader, FakeClient

FIXTURE_PATH = Path(__file__).parent / "fixtures"


class TestEvent(FixtureLoader, TestCase):
    data_dir = FIXTURE_PATH / "events"

    @staticmethod
    def join_event(idata):
        server = Server.objects.create(id=idata.author.guild.id, name=idata.author.guild.name)
        # initiator
        initiator_id = idata.author.id
        Profile.objects.create(
            uid=initiator_id, server=server, channel=idata.channel.id, last_known_nickname=idata.author.name
        )

        discord_client = FakeClient(
            {
                initiator_id: {"last_known_nickname": idata.author.name, "server": server, "channel": idata.channel.id},
            }
        )
        return initiator_id, discord_client, server

    def _test_event_cooldown_created(self, idata, confirm_data):
        initiator_id, discord_client, server = self.join_event(idata)

        self.assertEqual(CoolDown.objects.filter(profile_id=initiator_id).count(), 0)
        handler = CoolDownHandler(discord_client, idata, server)
        handler.handle()
        self.assertEqual(CoolDown.objects.filter(profile_id=initiator_id).count(), 1)
        return initiator_id, discord_client, server

    def test_not_so_mini_boss(self):
        idata, confirm_data = self.unpack_activities("not_so_mini_boss", "accepted")
        initiator_id, discord_client, server = self._test_event_cooldown_created(idata, confirm_data)

        handler = RPGHandler(discord_client, confirm_data, server)
        handler.handle()
        self.assertEqual(CoolDown.objects.count(), 1)

    @unittest.skip("rejections don't have a profile embed so we don't know who it's for; skipping for now.")
    def test_not_so_mini_boss_rejected(self):
        idata, confirm_data = self.unpack_activities("not_so_mini_boss", "rejected")
        initiator_id, discord_client, server = self._test_event_cooldown_created(idata, confirm_data)

        handler = RPGHandler(discord_client, confirm_data, server)
        handler.handle()
        self.assertEqual(CoolDown.objects.count(), 0)

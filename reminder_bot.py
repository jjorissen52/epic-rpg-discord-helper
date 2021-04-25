import re
import asyncio
import discord
import logging

from asgiref.sync import sync_to_async

# imported for side effects which setup django apps
from epic_reminder import wsgi  # noqa

from epic.models import GroupActivity
from epic.query import (
    get_cooldown_messages,
    get_guild_cooldown_messages,
    set_guild_membership,
)
from epic.handlers import rcd, rpg

logger = logging.getLogger(__name__)


class Client(discord.Client):
    async def on_ready(self):
        print("Logged on as {0}!".format(self.user))

    async def on_message(self, message):
        handler = rcd.RCDHandler(self, message)
        messages, (sync_function, args) = await sync_to_async(handler.handle)()
        await handler.send_messages(messages)
        await handler.perform_coroutine(sync_function, *args)
        server, content = await handler.aget_server(), handler.content

        handler = rpg.CoolDownHandler(self, message, server)
        await sync_to_async(handler.handle)()

        handler = await sync_to_async(rpg.RPGHandler)(self, message, server)
        await handler.perform_coroutine(handler.handle)

    async def on_message_edit(self, before, after):
        guild_name_regex = re.compile(r"\*\*(?P<guild_name>[^\*]+)\*\* members")
        player_name_regex = re.compile(r"\*\*(?P<player_name>[^\*]+)\*\*")
        guild_membership = {}
        guild_id_map = {}
        for embed in after.embeds:
            for field in embed.fields:
                name_match = guild_name_regex.match(field.name)
                if name_match:
                    guild_membership[name_match.group(1)] = player_name_regex.findall(field.value)
                break
            break
        for guild, membership_set in guild_membership.items():
            guild_id_map[guild] = []
            for member in membership_set:
                # careful in case name contains multiple #
                split_name = member.split("#")
                name, discriminator = "#".join(split_name[:-1]), split_name[-1]
                user = discord.utils.get(self.get_all_members(), name=name, discriminator=discriminator)
                if user:
                    guild_id_map[guild].append(user.id)
        await set_guild_membership(guild_id_map)


def main():
    from django.conf import settings

    intents = discord.Intents.default()
    intents.members = True

    bot = Client(intents=intents)

    async def _notify():
        await bot.wait_until_ready()
        while not bot.is_closed():
            try:
                await sync_to_async(GroupActivity.objects.delete_stale)()
                cooldown_messages = [
                    *await get_cooldown_messages(),
                    *await get_guild_cooldown_messages(),
                ]
                for message, channel in cooldown_messages:
                    _channel = await bot.fetch_channel(channel)
                    await _channel.send(message)
                # coode in here
            except (Exception, BaseException):
                logger.exception("could not send reminder message")
            finally:
                await asyncio.sleep(5)  # task runs every 5 seconds

    async def notify():
        while 1:
            await _notify()

    bot.loop.create_task(notify())
    bot.run(settings.DISCORD_TOKEN)


if __name__ == "__main__":
    main()

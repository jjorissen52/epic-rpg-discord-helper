import os
import re
import asyncio
import dotenv
import discord

dotenv.load_dotenv(override=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "epic_reminder.settings")

# django.setup() is called as a side-effect
from django.core.wsgi import get_wsgi_application

get_wsgi_application()

from epic.models import CoolDown, Profile, Server, JoinCode
from epic.query import get_instance, update_instance, upsert_cooldowns, bulk_delete, get_cooldown_messages
from epic.utils import tokenize

from epic.cmd_chain import handle_rpcd_message


class Client(discord.Client):
    async def on_ready(self):
        print("Logged on as {0}!".format(self.user))

    async def on_message(self, message):
        if message.author == self.user:
            return

        server = await get_instance(Server, id=message.channel.guild.id)
        if server and not server.active:
            return

        content = message.content[:150].lower()

        if content.startswith("rpgcd") or content.startswith("rcd"):
            if content.startswith("rcd"):
                tokens = tokenize(message.content[3:])
            else:
                tokens = tokenize(message.content[5:])
            msg = await handle_rpcd_message(self, tokens, message, server, None, None)
            embed = msg.to_embed()
            await message.channel.send(embed=embed)

        if not server:
            return

        # we want to pull the results of Epic RPG's cooldown message
        if str(message.author) == "EPIC RPG#4117":
            for embed in message.embeds:
                if getattr(embed.author, "name", None) and "cooldown" in embed.author.name:
                    # the user mentioned
                    user_id = embed.author.icon_url.strip("https://cdn.discordapp.com/avatars/").split("/")[0]
                    user = self.get_user(int(user_id))
                    profile, _ = await get_instance(
                        Profile,
                        uid=user_id,
                        defaults={
                            "last_known_nickname": user.name,
                            "server": server,
                            "channel": message.channel.id,
                        },
                    )
                    if profile.server_id != server.id or profile.channel != message.channel.id:
                        profile = await update_instance(profile, server_id=server.id, channel=message.channel.id)
                    # is the cooldowns list
                    if "cooldowns" in embed.author.name:
                        update, delete = CoolDown.from_cd(profile, [field.value for field in embed.fields])
                        await upsert_cooldowns(update)
                        await bulk_delete(CoolDown, delete)
                    elif "cooldown" in embed.author.name:
                        for cue, cooldown_type in CoolDown.COOLDOWN_RESPONSE_CUE_MAP.items():
                            if cue in str(embed.title):
                                await upsert_cooldowns(
                                    CoolDown.from_cooldown_reponse(profile, embed.title, cooldown_type)
                                )
            return

        if content.startswith("rpg"):
            cooldown_type, after = CoolDown.cd_from_command(message.content[3:])
            if not cooldown_type:
                return
            profile, _ = await get_instance(
                Profile,
                uid=message.author.id,
                defaults={
                    "last_known_nickname": message.author.name,
                    "server": server,
                    "channel": message.channel.id,
                },
            )
            if profile.server_id != server.id or profile.channel != message.channel.id:
                profile = await update_instance(profile, server_id=server.id, channel=message.channel.id)
            await upsert_cooldowns([CoolDown(profile=profile, type=cooldown_type, after=after)])


if __name__ == "__main__":
    from django.conf import settings

    bot = Client()

    async def notify():
        await bot.wait_until_ready()
        while not bot.is_closed():
            cooldown_cleanup = []
            cooldown_messages = await get_cooldown_messages()
            for _id, cd_type, channel, uid in cooldown_messages:
                _channel = await bot.fetch_channel(channel)
                await _channel.send(f"<@{uid}> {CoolDown.COOLDOWN_TEXT_MAP[cd_type]} (**{cd_type.title()}**)")
                cooldown_cleanup.append(_id)
            await bulk_delete(CoolDown, id__in=cooldown_cleanup)
            await asyncio.sleep(5)  # task runs every 5 seconds

    bot.loop.create_task(notify())
    bot.run(settings.DISCORD_TOKEN)

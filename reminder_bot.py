import os
import re
import dotenv
import discord

dotenv.load_dotenv(override=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "epic_reminder.settings")

# django.setup() is called as a side-effect
from django.core.wsgi import get_wsgi_application

get_wsgi_application()

from epic.models import CoolDown, Profile, Server, JoinCode, get_instance, update_instance, upsert_cooldowns
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

        if message.content.startswith("rpgcd"):
            tokens = tokenize(message.content[5:])
            msg = await handle_rpcd_message(tokens, message, server, None, None)
            await message.channel.send(msg.msg)

        if not server:
            return

        # we want to pull the results of Epic RPG's cooldown message
        if str(message.author) == "EPIC RPG#4117":
            for embed in message.embeds:
                if not getattr(embed.author, "name", None) or not "cooldowns" in embed.author.name:
                    return
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
                if profile.server_id != server.id:
                    update_instance(profile, server_id=server.id)
                if profile:
                    await upsert_cooldowns(CoolDown.from_cd(profile, [field.value for field in embed.fields]))
            return

        if message.content.startswith("rpg"):
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
            await upsert_cooldowns([CoolDown(profile=profile, type=cooldown_type, after=after)])


if __name__ == "__main__":
    from django.conf import settings

    bot = Client()
    bot.run(settings.DISCORD_TOKEN)

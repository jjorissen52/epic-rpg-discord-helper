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


class Client(discord.Client):
    async def on_ready(self):
        print("Logged on as {0}!".format(self.user))

    async def on_message(self, message):
        if message.author == self.user:
            return

        content = message.content
        if content.startswith("rpgcd"):
            tokens = tokenize(content[5:])
            if len(tokens) > 1 and tokens[0] == "register":
                join_code = await get_instance(JoinCode, code=tokens[1], claimed=False)
                if not join_code:
                    return await message.channel.send("That is not a valid Join Code.")
                server, created = await get_instance(
                    Server,
                    id=message.channel.guild.id,
                    active=True,
                    defaults={"name": message.channel.guild.name, "code": join_code},
                )
                if created:
                    await update_instance(join_code, claimed=True)
                    return await message.channel.send(f"Welcome {message.channel.guild.name}!")
                return await message.channel.send(f"{message.channel.guild.name} has already joined! Hello again!")

        server = await get_instance(Server, id=message.channel.guild.id, active=True)
        if not server:
            return

        if str(message.author) == "EPIC RPG#4117":
            for embed in message.embeds:
                if not getattr(embed.author, "name", None) or not "cooldown" in embed.author.name:
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
                    },
                )
                if profile.server != server:
                    update_instance(profile, server=server)
                if profile:
                    await upsert_cooldowns(CoolDown.from_cd(profile, [field.value for field in embed.fields]))
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
                },
            )
            await upsert_cooldowns([CoolDown(profile=profile, type=cooldown_type, after=after)])


if __name__ == "__main__":
    from django.conf import settings

    bot = Client()
    bot.run(settings.DISCORD_TOKEN)

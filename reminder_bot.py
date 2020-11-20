import os
import re
import dotenv
import discord

dotenv.load_dotenv(override=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "epic_reminder.settings")

# django.setup() is called as a side-effect
from django.core.wsgi import get_wsgi_application

get_wsgi_application()

from epic.models import CoolDown, Profile, Server, get_instance, upsert_cooldowns


class Client(discord.Client):
    async def on_ready(self):
        print("Logged on as {0}!".format(self.user))

    async def on_message(self, message):
        if message.author == self.user:
            return
        # if this is not a registered server, we say NO
        # (because the bot is inefficient and computational power is at a premium)
        if not await get_instance(Server, id=message.channel.guild.id, active=True):
            return

        if str(message.author) == "EPIC RPG#4117":
            for embed in message.embeds:
                if not getattr(embed.author, "name", None) or not "cooldown" in embed.author.name:
                    return
                # the user mentioned
                user_id = embed.author.icon_url.strip("https://cdn.discordapp.com/avatars/").split("/")[0]
                user = self.get_user(int(user_id))
                profile, _ = await get_instance(Profile, uid=user_id, defaults={"last_known_nickname": user.name})
                if profile:
                    await upsert_cooldowns(CoolDown.from_cd(profile, [field.value for field in embed.fields]))
            return

        if message.content.startswith("rpg"):
            cooldown_type, after = CoolDown.cd_from_command(message.content[3:])
            if not cooldown_type:
                return
            profile, _ = await get_instance(
                Profile, uid=message.author.id, defaults={"last_known_nickname": message.author.name}
            )
            await upsert_cooldowns([CoolDown(profile=profile, type=cooldown_type, after=after)])

        if message.content.startswith("rpgcd"):
            print("word")


if __name__ == "__main__":
    from django.conf import settings

    bot = Client()
    bot.run(settings.DISCORD_TOKEN)

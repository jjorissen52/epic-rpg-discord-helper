import os
import dotenv
import discord

dotenv.load_dotenv(override=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "epic_reminder.settings")

# django.setup() is called as a side-effect
from django.core.wsgi import get_wsgi_application

get_wsgi_application()


from asgiref.sync import sync_to_async
from epic.models import get_profile, upsert_cooldowns, CoolDown


class Client(discord.Client):
    async def on_ready(self):
        print("Logged on as {0}!".format(self.user))

    async def on_message(self, message):
        if message.author == client.user:
            return

        if str(message.author) == "EPIC RPG#4117":
            for embed in message.embeds:
                try:
                    # the user mentioned
                    user_id = embed.author.icon_url.strip("https://cdn.discordapp.com/avatars/").split("/")[0]
                    user = self.get_user(int(user_id))
                    profile = await get_profile(uid=user_id)
                    await upsert_cooldowns(CoolDown.from_cd(profile, [field.value for field in embed.fields]))
                except:  # noqa
                    raise
        # print('Message from {0.author}: {0.content}'.format(message))


if __name__ == "__main__":
    from django.conf import settings

    client = Client()
    client.run(settings.DISCORD_TOKEN)

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

from epic.models import CoolDown, Profile, Server, JoinCode, Gamble, Hunt
from epic.query import (
    get_instance,
    update_instance,
    upsert_cooldowns,
    bulk_delete,
    get_cooldown_messages,
    get_guild_cooldown_messages,
    set_guild_cd,
    set_guild_membership,
    update_hunt_results,
)
from epic.utils import tokenize

from epic.cmd_chain import handle_rpcd_message


async def process_rpg_messages(client, server, message):
    rpg_cd_rd_cues, cooldown_cue = ["cooldowns", "ready"], "cooldown"
    gambling_cues = set(Gamble.GAME_CUE_MAP.keys())
    cues = [*rpg_cd_rd_cues, *gambling_cues, cooldown_cue]
    if "found and killed" in message.content:
        hunt_result = Hunt.save_hunt_result(message)
        if hunt_result:
            name, *other = hunt_result
            possible_userids = [str(m.id) for m in client.get_all_members() if name == m.name]
            return await update_hunt_results(other, possible_userids)
    for embed in message.embeds:
        if getattr(embed.author, "name", None) and any([cue in embed.author.name for cue in cues]):
            # the user mentioned
            user_id = embed.author.icon_url.strip("https://cdn.discordapp.com/avatars/").split("/")[0]
            user = client.get_user(int(user_id))
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
            if any([cue in embed.author.name for cue in rpg_cd_rd_cues]):
                update, delete = CoolDown.from_cd(profile, [field.value for field in embed.fields])
                await upsert_cooldowns(update)
                await bulk_delete(CoolDown, delete)
            elif cooldown_cue in embed.author.name:
                for cue, cooldown_type in CoolDown.COOLDOWN_RESPONSE_CUE_MAP.items():
                    if cue in str(embed.title):
                        cooldowns = CoolDown.from_cooldown_reponse(profile, embed.title, cooldown_type)
                        if cooldowns and cooldown_type == "guild":
                            return await set_guild_cd(profile, cooldowns[0].after)
                        await upsert_cooldowns(cooldowns)
            elif any([cue in embed.author.name for cue in gambling_cues]):
                gamble = Gamble.from_results_screen(profile, embed)
                if gamble:
                    await gamble.asave()
    return


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
            return await process_rpg_messages(self, server, message)

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
            if cooldown_type == "guild":
                return await set_guild_cd(profile)
            elif cooldown_type == "hunt":
                _, _ = await get_instance(Hunt, profile_id=profile.uid, target=None, defaults={"target": None})
            await upsert_cooldowns([CoolDown(profile=profile, type=cooldown_type, after=after)])

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


if __name__ == "__main__":
    from django.conf import settings

    intents = discord.Intents.default()
    intents.members = True

    bot = Client(intents=intents)

    async def notify():
        await bot.wait_until_ready()
        while not bot.is_closed():
            cooldown_messages = [
                *await get_cooldown_messages(),
                *await get_guild_cooldown_messages(),
            ]
            for message, channel in cooldown_messages:
                _channel = await bot.fetch_channel(channel)
                await _channel.send(message)
            await asyncio.sleep(5)  # task runs every 5 seconds

    bot.loop.create_task(notify())
    bot.run(settings.DISCORD_TOKEN)

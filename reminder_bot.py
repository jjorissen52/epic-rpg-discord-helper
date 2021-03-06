import re
import asyncio
import discord
import logging

from asgiref.sync import sync_to_async

# imported for side effects which setup django apps
from epic_reminder import wsgi # noqa
from epic.models import CoolDown, Profile, Server, Gamble, Hunt, GroupActivity
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
from epic.utils import tokenize, RCDMessage
from epic.cmd_chain import handle_rpcd_message

logger = logging.getLogger(__name__)


async def process_rpg_messages(client, server, message):
    rpg_cd_rd_cues, cooldown_cue, pet_screen_cue = ["cooldowns", "ready"], "cooldown", "'s pets"
    gambling_cues = set(Gamble.GAME_CUE_MAP.keys())
    # arena is special case since it does not show an icon_url
    group_cues = GroupActivity.ACTIVITY_SET - {"arena"}
    cues = [*rpg_cd_rd_cues, *gambling_cues, *group_cues, cooldown_cue, pet_screen_cue]
    hunt_result = Hunt.hunt_result_from_message(message)
    if hunt_result:
        name, *other = hunt_result
        possible_userids = [str(m.id) for m in client.get_all_members() if name == m.name]
        return await update_hunt_results(other, possible_userids)
    else:
        hunt_together_result = Hunt.hunt_together_from_message(message)
        if hunt_together_result:
            all_members = set(client.get_all_members())
            (name1, *other1), (name2, *other2) = hunt_together_result
            possible_userids1 = [str(m.id) for m in all_members if name1 == m.name]
            possible_userids2 = [str(m.id) for m in all_members if name2 == m.name]
            await asyncio.gather(
                update_hunt_results(other1, possible_userids1),
                update_hunt_results(other2, possible_userids2),
            )

    profile = None
    for embed in message.embeds:
        # the user mentioned
        profile = await sync_to_async(Profile.from_embed_icon)(client, server, message, embed)
        if profile and any([cue in embed.author.name for cue in cues]):
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
            elif pet_screen_cue in embed.author.name:
                pet_cooldowns, _ = CoolDown.from_pet_screen(profile, [field.value for field in embed.fields])
                return await upsert_cooldowns(pet_cooldowns)

            elif any([cue in embed.author.name for cue in gambling_cues]):
                gamble = Gamble.from_results_screen(profile, embed)
                if gamble:
                    await gamble.asave()
            elif any([cue in embed.author.name for cue in group_cues]):
                group_activity_type = None
                for activity_type in group_cues:
                    if activity_type in embed.author.name:
                        group_activity_type = activity_type
                        break
                else:
                    return
                group_activity = await sync_to_async(GroupActivity.objects.latest_group_activity)(
                    profile.uid, group_activity_type
                )
                if group_activity:
                    confirmed_group_activity = await sync_to_async(group_activity.confirm_activity)(embed)
                    if confirmed_group_activity:
                        await sync_to_async(confirmed_group_activity.save_as_cooldowns)()
        # special case of GroupActivity
        arena_match = GroupActivity.REGEX_MAP["arena"].search(str(embed.description))
        if arena_match:
            name = arena_match.group(1)
            group_activity = await sync_to_async(GroupActivity.objects.latest_group_activity)(name, "arena")
            if group_activity:
                confirmed_group_activity = await sync_to_async(group_activity.confirm_activity)(embed)
                if confirmed_group_activity:
                    await sync_to_async(confirmed_group_activity.save_as_cooldowns)()

    if profile and (profile.server_id != server.id or profile.channel != message.channel.id):
        profile = await update_instance(profile, server_id=server.id, channel=message.channel.id)
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

        if content.startswith("rpgcd") or content.startswith("rcd") or content.startswith("rrd"):
            if content.startswith("rcd"):
                tokens = tokenize(message.content[3:])
            elif content.startswith("rrd"):
                tokens = ["rd", *tokenize(message.content[3:])]
            else:
                tokens = tokenize(message.content[5:])
            msg, coro = await handle_rpcd_message(self, tokens, message, server, None, None)
            embed = msg.to_embed()
            await message.channel.send(embed=embed)
            if coro:
                coroutine_func, args = coro
                completed_message = await coroutine_func(*args)
                if isinstance(completed_message, RCDMessage):
                    await message.channel.send(embed=completed_message.to_embed())
                elif isinstance(completed_message, str):
                    await message.channel.send(completed_message)
                else:
                    print(f"expected a string or RCDMessage, got {completed_message}")

        if not server:
            return

        # we want to pull the results of Epic RPG's cooldown message
        if str(message.author) == "EPIC RPG#4117":
            return await process_rpg_messages(self, server, message)

        if content.startswith("rpg"):
            cooldown_type, default_duration = await sync_to_async(CoolDown.default_cmd_cd)(message.content[3:])
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
            elif cooldown_type in {"hunt", "adventure"}:
                _, _ = await sync_to_async(Hunt.initiated_hunt)(profile.uid, content)
            elif cooldown_type in GroupActivity.ACTIVITY_SET:
                tokens = tokenize(message.content[3:])
                # when a group activity is actually a solo activity...
                if tuple(tokens[:2]) not in {("big", "arena"), ("horse", "breeding"), ("not", "so")}:
                    # need to know the difference between dungeon and miniboss here
                    cooldown_type = "miniboss" if tokens[0] == "miniboss" else cooldown_type
                    return await sync_to_async(GroupActivity.create_from_tokens)(
                        cooldown_type, self, profile, server, message
                    )
            await upsert_cooldowns(
                [
                    CoolDown(profile=profile, type=cooldown_type).calculate_cd(
                        profile=profile, duration=default_duration, type=cooldown_type
                    )
                ]
            )

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

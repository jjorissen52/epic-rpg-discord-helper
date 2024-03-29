import re

import discord

from epic.handlers.base import Handler
from epic.models import Profile, CoolDown, Guild, Hunt, GroupActivity, Sentinel, Gamble
from epic.query import _upsert_cooldowns, update_hunt_results, _bulk_delete, _set_guild_membership
from epic.types import HandlerResult
from epic.utils import tokenize


class CoolDownHandler(Handler):
    _profile = None

    def __init__(self, client, incoming, server=None):
        super().__init__(client, incoming, server)
        tokens = tokenize(self.content)
        if tokens and tokens[0] == "rpg":
            self.tokens = tokens[1:]

    @property
    def should_trigger(self):
        return self.tokens and self.client.user != self.incoming.author and self.server and self.server.active

    @property
    def profile(self):
        if not self._profile:
            self._profile, _ = Profile.objects.get_or_create(
                uid=self.incoming.author.id,
                defaults={
                    "last_known_nickname": self.incoming.author.name,
                    "server": self.server,
                    "channel": self.incoming.channel.id,
                },
            )
        return self._profile

    def handle(self):
        if not self.should_trigger:
            return
        cooldown_type, default_duration, tokens = CoolDown.default_cmd_cd(self.content[3:])
        if not cooldown_type:
            return
        if self.profile.server_id != self.server.id or self.profile.channel != self.incoming.channel.id:
            self.profile.update(server_id=self.server.id, channel=self.incoming.channel.id)
        if cooldown_type == "guild":
            return Guild.set_cooldown_for(self.profile)
        if cooldown_type in ["hunt", "adventure"]:
            Hunt.initiated_hunt(self.profile.uid, self.content)
        elif cooldown_type in GroupActivity.ACTIVITY_SET:
            # when a group activity is actually a solo activity...
            if tuple(tokens[:2]) not in {("big", "arena"), ("not", "so")}:
                # need to know the difference between dungeon and miniboss here
                cooldown_type = "miniboss" if tokens[0] == "miniboss" else cooldown_type
                return GroupActivity.create_from_tokens(
                    cooldown_type, self.client, self.profile, self.server, self.incoming
                )
            else:
                Sentinel.objects.create(profile=self.profile, trigger=3, metadata=dict(cooldown_type=cooldown_type))

        _upsert_cooldowns(
            [
                CoolDown(profile=self.profile, type=cooldown_type).calculate_cd(
                    profile=self.profile, duration=default_duration, type=cooldown_type
                )
            ]
        )


class RPGHandler(Handler):
    profile = None
    embed = None
    content = None

    def __init__(self, client, incoming, server=None):
        super().__init__(client, incoming, server)
        if not self.should_trigger:
            return
        if self.incoming.embeds:
            self.content = self.incoming.content
            self.embed = self.incoming.embeds[0]
            self.profile = Profile.from_embed_icon(self.client, self.server, self.incoming, self.embed)

    @property
    def should_trigger(self):
        author_unique_name = f"{self.incoming.author.name}#{self.incoming.author.discriminator}"
        return author_unique_name == "EPIC RPG#4117" and self.server and self.server.active

    def check_cues(self, *cues):
        for cue in cues:
            if cue in self.embed.author.name:
                return cue

    def process_hunt_response(self):
        hunt_result = Hunt.hunt_result_from_message(self.incoming)
        if hunt_result:
            name, *other = hunt_result
            possible_userids = [str(m.id) for m in self.client.get_all_members() if name == m.name]
            return update_hunt_results(other, possible_userids)

        hunt_together_result = Hunt.hunt_together_from_message(self.incoming)
        if not hunt_together_result:
            return
        all_members = set(self.client.get_all_members())
        for hunt_result in hunt_together_result:
            name, *other = hunt_result
            possible_userids = [str(m.id) for m in all_members if name == m.name]
            update_hunt_results(other, possible_userids)

    def handle_arena(self):
        arena_match = GroupActivity.REGEX_MAP["arena"].search(str(self.embed.description))
        if arena_match:
            name = arena_match.group(1)
            group_activity = GroupActivity.objects.latest_group_activity(name, "arena")
            if group_activity:
                confirmed_group_activity = group_activity.confirm_activity(self.embed)
                if confirmed_group_activity:
                    confirmed_group_activity.save_as_cooldowns()

    def handle(self) -> HandlerResult:
        default_response = [], (None, ())
        if not self.should_trigger:
            return default_response
        self.process_hunt_response()
        if not self.profile:
            if self.embed:
                # special case of GroupActivity
                self.handle_arena()
            return default_response
        if self.profile.server_id != self.server.id or self.profile.channel != self.incoming.channel.id:
            self.profile.update(server_id=self.server.id, channel=self.incoming.channel.id)
        if self.check_cues("cooldowns", "ready"):
            update, delete = CoolDown.from_cd(self.profile, [field.value for field in self.embed.fields])
            _upsert_cooldowns(update), _bulk_delete(CoolDown, delete)
            return default_response
        if self.check_cues("cooldown"):  # EPIC Rpg has responded telling you the command is on cooldown
            for cue, cooldown_type in CoolDown.COOLDOWN_RESPONSE_CUE_MAP.items():
                if cue not in str(self.embed.title):
                    continue
                cooldowns = CoolDown.from_cooldown_reponse(self.profile, self.embed.title, cooldown_type)
                if cooldowns and cooldown_type == "guild":
                    Guild.set_cooldown_for(self.profile, cooldowns[0].after)
                    return default_response
                _upsert_cooldowns(cooldowns)
                return default_response
        if self.check_cues("'s pets"):  # the user has opened their pet screen
            pet_cooldowns, _ = CoolDown.from_pet_screen(self.profile, [field.value for field in self.embed.fields])
            _upsert_cooldowns(pet_cooldowns)
            return default_response
        if self.check_cues("'s inventory"):
            return [], (Sentinel.act, (self.content, self.embed, self.profile, "inventory"))
        if self.check_cues(*Gamble.GAME_CUE_MAP):
            gamble = Gamble.from_results_screen(self.profile, self.embed)
            gamble.save()
            return default_response
        if "registered" in self.content:
            return [], (Sentinel.act, (self.content, self.embed, self.profile, "registration_confirmation"))

        group_activity_type = self.check_cues(*(GroupActivity.ACTIVITY_SET - {"arena"}))
        if group_activity_type:
            group_activity = GroupActivity.objects.latest_group_activity(self.profile.uid, group_activity_type)
            if group_activity:
                confirmed_group_activity = group_activity.confirm_activity(self.embed)
                if confirmed_group_activity:
                    confirmed_group_activity.save_as_cooldowns()
        return default_response


class GuildListHandler(Handler):
    embed = None

    def __init__(self, client, incoming, server=None):
        super().__init__(client, incoming, server)
        if not self.should_trigger:
            return
        self.embed = self.incoming.embeds[0]

    @property
    def should_trigger(self):
        return (
            str(self.incoming.author) == "EPIC RPG#4117" and self.server and self.server.active and self.incoming.embeds
        )

    def handle(self):
        guild_name_regex = re.compile(r"\*\*(?P<guild_name>[^\*]+)\*\* members")
        player_name_regex = re.compile(r"\*\*(?P<player_name>[^\*]+)\*\*")
        guild_membership = {}
        guild_id_map = {}
        for field in self.embed.fields:
            name_match = guild_name_regex.match(field.name)
            if name_match:
                guild_membership[name_match.group(1)] = player_name_regex.findall(field.value)
        for guild, membership_set in guild_membership.items():
            guild_id_map[guild] = []
            for member in membership_set:
                # careful in case name contains multiple #
                split_name = member.split("#")
                name, discriminator = "#".join(split_name[:-1]), split_name[-1]
                user = discord.utils.get(self.client.get_all_members(), name=name, discriminator=discriminator)
                if user:
                    guild_id_map[guild].append(user.id)
        _set_guild_membership(guild_id_map)

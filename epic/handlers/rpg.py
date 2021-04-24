from epic.handlers.base import Handler
from epic.models import Profile, CoolDown, Guild, Hunt, GroupActivity
from epic.query import _upsert_cooldowns
from epic.utils import tokenize


class CoolDownHandler(Handler):
    _profile = None

    def __init__(self, clint, incoming, server=None):
        super().__init__(clint, incoming, server)
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
        cooldown_type, default_duration = CoolDown.default_cmd_cd(self.content[3:])
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
            if tuple(self.tokens[:2]) not in {("big", "arena"), ("horse", "breeding"), ("not", "so")}:
                # need to know the difference between dungeon and miniboss here
                cooldown_type = "miniboss" if self.tokens[0] == "miniboss" else cooldown_type
                return GroupActivity.create_from_tokens(
                    cooldown_type, self.client, self.profile, self.server, self.incoming
                )
        _upsert_cooldowns(
            [
                CoolDown(profile=self.profile, type=cooldown_type).calculate_cd(
                    profile=self.profile, duration=default_duration, type=cooldown_type
                )
            ]
        )

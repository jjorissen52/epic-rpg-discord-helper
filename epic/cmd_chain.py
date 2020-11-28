import re
import pytz
import discord
import datetime
import operator
import functools

from asgiref.sync import sync_to_async
from pipeline import execution_pipeline

from django.forms.models import model_to_dict

from epic.models import CoolDown, Profile, Server, JoinCode, Gamble, Hunt
from epic.utils import tokenize


class RCDMessage:
    color = 0x8C8A89
    title = None
    footer = None
    fields = []

    def __init__(self, msg, title=None, footer=None, fields=None):
        self.msg = msg
        if title:
            self.title = title
        if footer:
            self.footer = footer
        if fields:
            self.fields = fields

    def to_embed(self):
        kwargs = {"color": self.color, "description": self.msg}
        if self.title:
            kwargs["title"] = self.title
        embed = discord.Embed(**kwargs)
        for field in self.fields:
            embed.add_field(name=field[0], value=field[1], inline=False)
        if self.footer:
            embed.set_footer(text=self.footer)
        return embed


class ErrorMessage(RCDMessage):
    title = "Error"
    color = 0xEB4034


class NormalMessage(RCDMessage):
    color = 0x4381CC


class HelpMessage(RCDMessage):
    title = "Help"


class SuccessMessage(RCDMessage):
    color = 0x628F47


def params_as_args(func):
    arg_names = ["client", "tokens", "message", "server", "profile", "msg", "help"]

    @functools.wraps(func)
    def wrapper(params):
        if params["msg"] or params.get("error", None):
            # short-circuit to prevent running
            # the rest of the command chain
            return params
        # if they are using commands, we want to go ahead and
        # make them a profile.
        if params["profile"] is None:
            message, server, tokens, help = params["message"], params["server"], params["tokens"], params["help"]
            if server is not None:
                profile, created = Profile.objects.get_or_create(
                    uid=message.author.id,
                    defaults={
                        "last_known_nickname": message.author.name,
                        "server": server,
                        "channel": message.channel.id,
                    },
                )
                if not created and profile.server_id != server.id:
                    profile.update(server_id=server.id)
                params["profile"] = profile
            elif not help and tokens and tokens[0] not in {"help", "register"}:
                params["msg"] = ErrorMessage(
                    "You can only use `help` and `register` commands until "
                    f"{message.channel.guild.name} has used a join code."
                )
        args = [params.get(arg_name, None) for arg_name in arg_names]
        res = func(*args)
        if not res:
            return params
        params.update(res)
        return params

    return wrapper


@params_as_args
def _help(client, tokens, message, server, profile, msg, help=None, error=None):
    """

    Call `help` on an available command to see it's usage. Example:
    `rcd help register`
    `rcd h register`
    `rcd h notify`

    Available Commands:
        • `rcd register`
        • `rcd profile|p [<profile_command>]`
        • `rcd on`
        • `rcd off`
        • `rcd cd` or `rcd`
        • `rcd timezone|tz <timezone>`
        • `rcd timeformat|tf "<format_string>"`
        • `rcd notify|n <command_type> on|off`
        • `rcd <command_type> on|off` (e.g. `rcd hunt on` same as `rcd notify hunt on`)
        • `rcd whocan|w <command_type>`
        • `rcd dibbs|d`
        • `rcd gamling|g [num_minutes] [@player]`
        • `rcd drops|dr [num_minutes] [@player]`
        • `rcd hunts|hu [num_minutes] [@player]`

    This bot attempts to determine the cooldowns of your EPIC RPG commands
    and will notify you when it thinks your commands are available again.
    Cooldowns are determined in two ways:
        • The cooldown duration for an observed EPIC RPG command is added to the current time. A notification is scheduled for this time.
        • The output of `rpg cd` is extracted and used to schedule notifications for all commands currently on cooldown.
    """
    if not tokens:
        # default command is now cd instead of help
        return {"tokens": ["cd"]}
    if tokens[0] not in {"help", "h"}:
        return
    if len(tokens) == 1:
        return {"msg": HelpMessage(_help.__doc__)}
    return {"help": True, "tokens": tokens[1:]}


@params_as_args
def cd(client, tokens, message, server, profile, msg, help=None):
    """
    Display when your cooldowns are expected to be done.
    Usage:
        • `rcd cd [<cooldown_types> [...<cooldown_types>]]`
    Example:
        • `rcd cd`
        • `rcd`
        • `rcd daily weekly`
    """
    implicit_invocation = False
    if tokens[0] in CoolDown.COOLDOWN_MAP or re.match(r"<@!?(?P<user_id>\d+)>", tokens[0]):
        # allow implicit invocation of cd
        tokens, implicit_invocation = ["cd", *tokens], True
    nickname = message.author.name
    cooldown_filter = lambda x: True  # show all filters by default
    if tokens[0] != "cd":
        return None
    if help and len(tokens) == 1:
        return {"msg": HelpMessage(cd.__doc__)}
    elif len(tokens) > 1:
        mentioned_profile = Profile.from_tag(tokens[1], client, server, message)
        if mentioned_profile:
            profile = mentioned_profile
            cd_args = set(tokens[2:])
            nickname = profile.last_known_nickname
        else:
            cd_args = set(tokens[1:])
        # means there are cooldown type arguments to filter on
        if cd_args:
            cooldown_filter = lambda x: x in cd_args

    profile_tz = pytz.timezone(profile.timezone)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    default = datetime.datetime(1790, 1, 1, tzinfo=datetime.timezone.utc)
    msg = ""
    cooldowns = {
        _cd[0]: _cd[1]
        for _cd in CoolDown.objects.filter(profile_id=profile.pk).order_by("after").values_list("type", "after")
    }
    all_cooldown_types = set([c[0] for c in CoolDown.COOLDOWN_TYPE_CHOICES])
    if not profile.player_guild:
        all_cooldown_types = all_cooldown_types - {"guild"}
    else:
        cooldowns["guild"] = profile.player_guild.after if profile.player_guild.after else default
    selected_cooldown_types = sorted(
        filter(cooldown_filter, all_cooldown_types),
        key=lambda x: cooldowns[x] if x in cooldowns else default,
    )
    for cooldown_type in selected_cooldown_types:
        after = cooldowns.get(cooldown_type, None)
        if after:
            if after > now:
                cooldown_after = cooldowns[cooldown_type].astimezone(profile_tz)
                msg += f":clock2: `{cooldown_type:12} {cooldown_after.strftime(profile.time_format):>20}`\n"
        else:
            msg += f":white_check_mark: `{cooldown_type:12} {'Ready!':>20}` \n"
    if not msg:
        msg = "Please use `rpg cd` or an EPIC RPG command to populate your cooldowns.\n"
    return {"msg": NormalMessage(msg, title=f"**{nickname}'s** Cooldowns ({profile.timezone})")}


@params_as_args
def register(client, tokens, message, server, profile, msg, help=None, error=None):
    """
        Register your server for use with Epic Reminder.
    Compute resources are limited, so invite codes will be doled out sparingly.
    Example:
        • `rcd register asdf` attempts to register the server using the join code `asdf`
    """
    if tokens[0] != "register":
        return None
    if help or len(tokens) == 1:
        return {"msg": HelpMessage(register.__doc__)}
    if server:
        return {"msg": NormalMessage(f"{message.channel.guild.name} has already joined! Hello again!", title="Hi!")}
    if len(tokens) > 1:
        cmd, *args = tokens
    else:
        cmd, args = tokens[0], ()
    if not args:
        return {"msg": ErrorMessage("You must provide a join code to register.", title="Registration Error")}
    join_code = JoinCode.objects.filter(code=args[0], claimed=False).first()
    if not join_code:
        return {"msg": ErrorMessage("That is not a valid Join Code.", title="Invalid Join Code")}
    server = Server.objects.create(id=message.channel.guild.id, name=message.channel.guild.name, code=join_code)
    join_code.claim()
    return {"msg": SuccessMessage(f"Welcome {message.channel.guild.name}!", title="Welcome!")}


@params_as_args
def _profile(client, tokens, message, server, profile, msg, help=None):
    """
    When called without any arguments, e.g. `rcd profile` this will display
    profile-related information. Otherwise, it will treat your input as a profile related sub-command.

    Available Commands:
        • `rcd profile|p`
        • `rcd profile|p timezone|tz <timezone>`
        • `rcd profile|p timeformat|tf "<format_string>"`
        • `rcd profile|p on|off`
        • `rcd profile|p [notify|n] <cooldown_type> on|off`
        • `rcd profile|p gamling|g [@player]`
    Examples:
        • `rcd profile` Displays your profile information
        • `rcd p tz <timezone>` Sets your timezone to the provided timezone.
        • `rcd p on` Enables notifications for your profile.
        • `rcd p notify hunt on` Turns on hunt notifications for your profile.
        • `rcd p hunt on` Turns on hunt notifications for your profile.
    """
    if tokens[0] not in {"profile", "p"}:
        return None
    if help and len(tokens) == 1:
        return {"msg": HelpMessage(_profile.__doc__)}
    elif len(tokens) > 1:
        # allow other commands to be namespaced by profile if that's how the user calls it
        if tokens[1] in {
            *("timezone", "tz"),
            *("timeformat", "tf"),
            *("notify", "n"),
            *("gambling", "g"),
            "on",
            "off",
            # allow implicit command type commands to be namespaced by `rcd p`
            *CoolDown.COOLDOWN_MAP.keys(),
        }:
            return {"tokens": tokens[1:]}
        return {"error": 1}
    notifications = ""
    for k, v in model_to_dict(profile).items():
        if isinstance(v, bool):
            notifications += f"{':ballot_box_with_check:' if v else ':x:'} `{k:25}`\n"
    return {
        "msg": NormalMessage(
            "",
            fields=(
                ("Nickname", profile.last_known_nickname),
                ("Timezone", f"`{profile.timezone}`"),
                ("Time Format", f"`{profile.time_format}`"),
                ("Notications Enabled", notifications),
            ),
        )
    }


@params_as_args
def notify(client, tokens, message, server, profile, msg, help=None):
    """
        Manage your notification settings. Here you can specify which types of
    epic rpg commands you would like to receive reminders for. For example, you can
    enable or disable showing a reminder for when `rpg hunt` should be available. All reminders
    are enabled by defailt. Example usage:
        • `rcd notify hunt on` Will turn on cd notifcations for `rpg hunt`.
        • `rcd daily on` Will turn on cd notifcations for `rpg daily`.
        • `rcd n hunt off` Will turn off notifications for `rpg hunt`
        • `rcd n weekly on` Will turn on notifications for `rpg weekly`
        • `rcd n all off` Will turn off all notifications (but `profile.notify == True`)

    Command Types:
        • `all`
        • `daily`
        • `weekly`
        • `lootbox`
        • `vote`
        • `hunt`
        • `adventure`
        • `training`
        • `duel`
        • `quest`
        • `work` (chop, mine, fish, etc.)
        • `horse`
        • `arena`
        • `dungeon`
    """
    if (tokens[0] in CoolDown.COOLDOWN_MAP or tokens[0] == "all") and tokens[-1] in {"on", "off"}:
        # allow implicit invocation of notify
        tokens = ["notify", *tokens]
        # make sure all passed tokens are valid cooldown type
        for token in {*tokens[1:-1]}:
            if token not in CoolDown.COOLDOWN_MAP and token != "all":
                return {"error": 1}
    if tokens[0] not in {"notify", "n"} or len(tokens) == 2:
        return None
    if help or len(tokens) == 1:
        return {"msg": HelpMessage(notify.__doc__)}
    _, command_type, toggle = tokens
    if (command_type in CoolDown.COOLDOWN_MAP or command_type == "all") and toggle in {"on", "off"}:
        on = toggle == "on"
        if command_type == "all":
            kwargs = {command_name: on for _, command_name in CoolDown.COOLDOWN_TYPE_CHOICES}
        else:
            # "work" is stored as "mine" in the database
            command_type = "work" if command_type == "mine" else command_type
            kwargs = {command_type: on}
        profile.update(last_known_nickname=message.author.name, **kwargs)
        if not profile.notify:
            return {
                "msg": NormalMessage(
                    f"Notifications for `{command_type}` are now {toggle} for **{message.author.name}** "
                    "but you will need to turn on notifications before you can receive any. "
                    "Try `rcd on` to start receiving notifcations."
                )
            }
        return {
            "msg": SuccessMessage(
                f"Notifications for **{command_type}** are now **{toggle}** for **{message.author.name}**."
            )
        }


@params_as_args
def toggle(client, tokens, message, server, profile, msg, help=None):
    """
    Toggle your profile notifications **{version}**. Example:
      • `rcd {version}`
    """
    if tokens[0] not in {"on", "off"}:
        return None
    on_or_off = tokens[0]
    if help and len(tokens) == 1:
        return {"msg": HelpMessage(toggle.__doc__.format(version=on_or_off))}
    elif len(tokens) != 1:
        return {"error": 1}

    profile.update(notify=on_or_off == "on")
    return {"msg": SuccessMessage(f"Notifications are now **{on_or_off}** for **{message.author.name}**.")}


@params_as_args
def timezone(client, tokens, message, server, profile, msg, help=None):
    """
    Set your timezone. Example:
        • `rcd timezone <timezone>` Sets your timezone to the provided timzone.
          (This only effects the time displayed in `rcd cd`; notification functionality
          is not effected.)
        • `rcd tz default` Sets your timezone back to the default.
    """
    command = tokens[0]
    if command not in {"timezone", "tz"}:
        return None
    current_time = datetime.datetime.now().astimezone(pytz.timezone(profile.timezone))
    if help or len(tokens) == 1:
        return {
            "msg": HelpMessage(
                timezone.__doc__,
                fields=[
                    (
                        "Info",
                        f"Current time with your time format `{profile.time_format}` "
                        f"in your timezone `{profile.timezone}` is {current_time.strftime(profile.time_format)}. \n"
                        f"[Visit this page to see a list of timezones.](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)",
                    )
                ],
            )
        }
    if len(tokens) == 2:
        # need case sensitive tokens to get correct timezone name,
        # need case insensitive tokens to get relative position in of
        # tz|timezone token from user input
        tokens = tokenize(message.content[:250], preserve_case=True)
        tz = tokens[-1]
        if tz.lower() == "default":
            tz = Profile.DEFAULT_TIMEZONE
        elif tz not in set(map(lambda x: x[0], Profile.TIMEZONE_CHOICES)):
            return {"msg": ErrorMessage(f"{tz} is not a valid timezone.")}
        else:
            profile.update(timezone=tz)
            return {
                "msg": SuccessMessage(
                    f"**{message.author.name}'s** timezone has been set to **{tz}**.",
                    fields=[
                        (
                            "Info",
                            f"Current time with your time format `{profile.time_format}` "
                            f"in your timezone `{profile.timezone}` is {current_time.strftime(profile.time_format)}. ",
                        )
                    ],
                )
            }


@params_as_args
def timeformat(client, tokens, message, server, profile, msg, help=None):
    """
    Set the time format for the output of rcd using Python
    `strftime` notation. Defaults to `%I:%M:%S %p, %m/%d`. If
    you don't know what that means, see the linked resource below.

    Usage:
        • `rcd timeformat|tf "<format_string>"`
    Examples:
        • `rcd timeformat "%I:%M:%S %p, %m/%d"` **Notice the quotes.** Very important!
        • `rcd tf "%Y-%m-%d %H:%M:%S"`
        • `rcd tf default` Restore your time format to default.

    Don't worry, you will not be able to save an invalid time format.
    """

    command = tokens[0]
    if command not in {"timeformat", "tf"}:
        return None
    itokens = tokenize(message.content[:250], preserve_case=True)
    current_time = datetime.datetime.now().astimezone(pytz.timezone(profile.timezone)).strftime(profile.time_format)
    if help or len(tokens) == 1:
        return {
            "msg": HelpMessage(
                timeformat.__doc__,
                fields=[
                    (
                        "Info",
                        f"Current time with your time format `{profile.time_format}` "
                        f"in your timezone `{profile.timezone}` is {current_time}. \n"
                        "[Visit here for documentation on time format strings.]"
                        "(https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes)",
                    )
                ],
            )
        }
    elif len(tokens) != 2:
        return {
            "msg": ErrorMessage(
                f"Could not parse {' '.join(itokens)} as a valid timeformat command; "
                "your input had more arguments than epected. "
                "Did you make sure to quote your format string?",
                title="Parse Error",
            )
        }
    # ensure tokens and itokens are the same lenth.
    time_format = itokens[-1]
    if len(time_format) > Profile.MAX_TIME_FORMAT_LENGTH:
        return {
            "msg": ErrorMessage(
                f"Your specified time format `{timeformat}` is too long. "
                f"It should have {len(time_format) - Profile.MAX_TIME_FORMAT_LENGTH} "
                "fewer characters.",
                title="Are you being naughty?",
            )
        }
    if time_format.lower() == "default":
        time_format = Profile.DEFAULT_TIME_FORMAT
    try:
        current_time = datetime.datetime.now().astimezone(pytz.timezone(profile.timezone)).strftime(time_format)
        profile.update(time_format=time_format)
        return {
            "msg": SuccessMessage(
                f"Great! You set your time format to `{time_format}`. " f"The current time is {current_time}",
                title="Good job!",
            )
        }
    except Exception as e:
        # I honestly am not sure if this is possible
        return {
            "msg": ErrorMessage(
                f"Great... Your time format `{time_format}` broke something; " f"err = {e}", "Oh boy Oh geez"
            )
        }


@params_as_args
def whocan(client, tokens, message, server, profile, msg, help=None):
    """
    Determine who in your server can use a particular command. Example:
      • `rcd whocan dungeon`
      • `rcd w dungeon`
    """
    if tokens[0] not in {"whocan", "w"}:
        return None
    if help or len(tokens) == 1:
        return {"msg": HelpMessage(whocan.__doc__)}

    rpg_command = " ".join(tokens[1:])
    if tokens[1] not in CoolDown.COMMAND_RESOLUTION_MAP:
        return {
            "msg": ErrorMessage(
                "`rcd whocan` should work with any group command "
                "that you can use with EPIC RPG. If you think this "
                "error is a mistake, let me know.",
                title=f"Invalid Command Type `{rpg_command}`",
            )
        }

    cooldown_type_func = CoolDown.COMMAND_RESOLUTION_MAP[tokens[1]]
    if len(tokens) > 2:
        cooldown_type = cooldown_type_func(" ".join(tokens[2:]))
    else:
        cooldown_type = cooldown_type_func(None)

    ats = [
        f"<@{uid}>"
        for uid in set(
            Profile.objects.exclude(uid=profile.uid)
            .exclude(cooldown__type=cooldown_type)
            .filter(server_id=message.channel.guild.id)
            .values_list("uid", flat=True)
        )
    ]
    if ats:
        msg = f"All of these players can `{rpg_command}`: \n\n" + "\n\t".join(ats)
        msg += f"\n\nExample: \n\n```rpg {rpg_command} {' '.join(ats)}\n\n```"
        return {"msg": SuccessMessage(msg, title=f"They can **{rpg_command.title()}**")}
    return {"msg": NormalMessage("Sorry, no one can do that right now.")}


@params_as_args
def dibbs(client, tokens, message, server, profile, msg, help=None):
    """
    Call "dibbs" on the guild raid.
    Usage:
        • `rcd dibbs|d[?]`
    Example:
        • `rcd dibbs` Call dibbs on next guild raid
        • `rcd dibbs?` Find out if anyone has dibbs without claiming it
    """
    if tokens[0] not in {"dibbs", "dibbs?", "d", "d?"}:
        return None
    if help:
        return {"msg": HelpMessage(dibbs.__doc__)}
    if not profile.player_guild:
        return {"msg": ErrorMessage(":disappointed: You aren't part of a guild.")}
    elif not profile.player_guild.after:
        return {
            "msg": ErrorMessage(
                "I don't know when the next guild raid is. Run `rpg guild raid` "
                "in a channel that I can see and try again."
            )
        }
    tz, tf = pytz.timezone(profile.timezone), profile.time_format
    after = profile.player_guild.after.astimezone(tz).strftime(tf)
    raid_dibbs = profile.player_guild.raid_dibbs
    if tokens[0][-1] == "?":
        if raid_dibbs:
            player_with_dibbs = client.get_user(int(raid_dibbs.uid))
            return {"msg": NormalMessage(f"**{player_with_dibbs}** has dibbs on the next guild raid at `{after}`.")}
        else:
            return {"msg": NormalMessage(f"No one has dibbs on the next guild raid at `{after}`.")}
    if not raid_dibbs:
        profile.player_guild.update(raid_dibbs=profile)
        return {"msg": SuccessMessage(f"Okay! You've got dibbs on the next guild raid at `{after}`!", title="Dibbsed!")}
    elif raid_dibbs == profile:
        return {
            "msg": NormalMessage(f"You've already got dibbs on the next guild raid at `{after}`!", title="Dibbsed!")
        }
    else:
        player_with_dibbs = client.get_user(int(raid_dibbs.uid))
        return {"msg": NormalMessage(f"Sorry, **{player_with_dibbs}** already has dibbs.", title="Not this time!")}


@params_as_args
def stats(client, tokens, message, server, profile, msg, help=None):
    """
    This command shows the output of {long} stats that the helper bot has managed to collect.
    Usage:
        • `rcd {long}|{short} [num_minutes] [@player]`
    Examples:
        • `rcd {long}` show your own {long} stats
        • `rcd {long} 3` for the last 3 minutes
        • `rcd {short} @player` show a player's {long} stats
    """
    minutes, _all = None, False
    token_map = {
        "gambling": ("gambling", "g"),
        "g": ("gambling", "g"),
        "drops": ("drops", "dr"),
        "dr": ("drops", "dr"),
        "hunts": ("hunts", "hu"),
        "hu": ("hunts", "hu"),
    }
    if tokens[0] not in token_map:
        return None
    long, short = token_map[tokens[0]]
    if help:
        return {"msg": HelpMessage(stats.__doc__.format(long=long, short=short))}
    if len(tokens) > 1:
        mentioned_profile = Profile.from_tag(tokens[-1], client, server, message)
        if mentioned_profile:
            tokens = tokens[:-1]
            profile = mentioned_profile
        elif tokens[-1] == "all":
            _all = True
            tokens = tokens[:-1]
        if re.match(r"^([0-9\* ]+)$", tokens[-1]):
            min_tokens, prod = tokens[-1].replace(" ", "").split("*"), 1
            minutes = functools.reduce(operator.mul, [int(t) for t in min_tokens], 1)
        if not mentioned_profile and not minutes and not _all:
            return {
                "msg": ErrorMessage(
                    f"`rcd {' '.join(tokens)}` is not valid invocation of `rcd {long}`. "
                    "Example usage: `rcd {short} 5 @player`",
                    title="Stats Usage Error",
                )
            }
    uid = None if _all else profile.uid
    name = server.name if _all else client.get_user(int(profile.uid)).name
    if long == "gambling":
        return {
            "msg": NormalMessage(
                "", fields=Gamble.objects.stats(uid, minutes, server.id), title=f"{name}'s Gambling Addiction"
            )
        }
    elif long == "hunts":
        return {
            "msg": NormalMessage("", fields=Hunt.objects.hunt_stats(uid, minutes, server.id), title=f"{name}'s Carnage")
        }
    elif long == "drops":
        return {
            "msg": NormalMessage("", fields=Hunt.objects.drop_stats(uid, minutes, server.id), title=f"{name}'s Drops")
        }


command_pipeline = execution_pipeline(
    pre=[
        _help,  # needs to be first to pass "help" param to those that follow
        whocan,
        # most commands that follow can be invoked as profile subcommand
        _profile,
        notify,  # notify must be before cd so `rcd hunt on` works
        # cd allows arbitrary arguments so it must follow
        # all other commands that can be invoked implicitly
        cd,
        stats,
        toggle,
        dibbs,
        timezone,
        timeformat,
        register,  # called rarely, should be last.
    ],
)


@sync_to_async
@command_pipeline
def handle_rpcd_message(client, tokens, message, server, profile, msg, help=None, error=None):
    if (error and not isinstance(error, str)) or not msg:
        original_tokens = tokenize(message.content[:250], preserve_case=True)
        return ErrorMessage(f"`{' '.join(original_tokens)}` could not be parsed as a valid command.")
    elif error:
        return ErrorMessage(error)
    return msg

import re
import time
import pytz
import decimal
import datetime
import operator
import functools

from django.db.models import Q
from django.forms.models import model_to_dict
from django.core.exceptions import ValidationError

from epic.cmd.registry import default_registry
from epic.models import Channel, CoolDown, Profile, Server, JoinCode, Gamble, Hunt, Event
from epic.utils import tokenize, ErrorMessage, NormalMessage, HelpMessage, SuccessMessage
from epic.history.scrape import scrape_channels, scrape_channel


register = default_registry


@register({"h", "help"})
def _help(client, tokens, message, server, profile, msg, help=None):
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
        • `rcd rd` or `rrd`
        • `rcd timezone|tz <timezone>`
        • `rcd timeformat|tf "<format_string>"`
        • `rcd multiplier|mp <multiplier>`
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
    if len(tokens) == 1:
        return {"msg": HelpMessage(_help.__doc__)}
    return {"help": True, "tokens": tokens[1:]}


@register(
    entry_tokens={"", "cd", "rd", *CoolDown.COOLDOWN_MAP.keys()},
    entry_patterns=[r"<@!?(?P<user_id>\d+)>"],
    token_filters=[lambda t: t[-1] not in {"on", "off"}],
)
def cd(client, tokens, message, server, profile, msg, help=None):
    """
    Display when your cooldowns are expected to be done.
    Usage:
        • `rcd cd [<cooldown_types> [...<cooldown_types>]]` shows all cooldowns
        • `rcd rd [<cooldown_types> [...<cooldown_types>]]` shows ready cooldowns
    Example:
        • `rcd cd`
        • `rcd` or `rrd`
        • `rcd daily weekly`
    """
    if tokens[0] not in {"cd", "rd"}:
        # allow for implicit or default invocation of rcd
        tokens = ["cd", *tokens[1:]] if tokens[0] == "" else ["cd", *tokens]
    nickname = message.author.name
    cooldown_filter = lambda x: True  # show all filters by default
    if tokens[0] not in {"rd", "cd"}:
        return None
    if help and len(tokens) == 1:
        return {"msg": HelpMessage(cd.__doc__)}
    elif len(tokens) > 1:
        mentioned_profile = Profile.from_tag(tokens[-1], client, server, message)
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
    msg, warn = "", False
    cooldowns = {
        _cd[0]: _cd[1]
        for _cd in CoolDown.objects.filter(profile_id=profile.pk).order_by("after").values_list("type", "after")
    }
    all_cooldown_types = set([c[0] for c in CoolDown.COOLDOWN_TYPE_CHOICES])
    if not profile.player_guild:
        all_cooldown_types = all_cooldown_types - {"guild"}
    else:
        warn = True if profile.player_guild.raid_dibbs else False
        cooldowns["guild"] = profile.player_guild.after if profile.player_guild.after else default
    selected_cooldown_types = sorted(
        filter(cooldown_filter, all_cooldown_types),
        key=lambda x: cooldowns[x] if x in cooldowns else default,
    )
    for cooldown_type in selected_cooldown_types:
        after = cooldowns.get(cooldown_type, None)
        if not after or after <= now:
            icon = ":warning:" if warn and cooldown_type == "guild" else ":white_check_mark:"
            warning = " (dibbs) " if warn and cooldown_type == "guild" else ""
            msg += f"{icon} `{cooldown_type + warning:15} {'Ready!':>20}` \n"
        elif tokens[0] == "cd":  # don't show if "rd" command
            cooldown_after = cooldowns[cooldown_type].astimezone(profile_tz)
            icon = ":warning:" if warn and cooldown_type == "guild" else ":clock2:"
            warning = " (dibbs) " if warn and cooldown_type == "guild" else ""
            msg += f"{icon} `{cooldown_type + warning:15} {cooldown_after.strftime(profile.time_format):>20}`\n"
    if not msg:
        msg = (
            "All commands on cooldown! (You may need to use `rpg cd` to populate your cooldowns for the first time.)\n"
        )
    return {"msg": NormalMessage(msg, title=f"**{nickname}'s** Cooldowns ({profile.timezone})")}


@register({"register"})
def _register(client, tokens, message, server, profile, msg, help=None):
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


@register({"profile", "p"})
def _profile(client, tokens, message, server, profile, msg, help=None):
    """
    When called without any arguments, e.g. `rcd profile` this will display
    profile-related information. Otherwise, it will treat your input as a profile related sub-command.

    Available Commands:
        • `rcd profile|p`
        • `rcd profile|p timezone|tz <timezone>`
        • `rcd profile|p timeformat|tf "<format_string>"`
        • `rcd profile|p multiplier|mp <multiplier>`
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
    if help and len(tokens) == 1:
        return {"msg": HelpMessage(_profile.__doc__)}
    elif len(tokens) > 1:
        # allow other commands to be namespaced by profile if that's how the user calls it
        if tokens[1] in {
            *("timezone", "tz"),
            *("timeformat", "tf"),
            *("multiplier", "mp"),
            *("notify", "n"),
            *("gambling", "g"),
            "on",
            "off",
            # allow implicit command type commands to be namespaced by `rcd p`
            *CoolDown.COOLDOWN_MAP.keys(),
        }:
            return {"tokens": tokens[1:]}
        maybe_profile = Profile.from_tag(tokens[1], client, server, message)
        if not maybe_profile:
            return {"error": 1}
        profile = maybe_profile
    notifications = ""
    for k, v in model_to_dict(profile).items():
        if isinstance(v, bool):
            notifications += f"{':ballot_box_with_check:' if v else ':x:'} `{k:25}`\n"
    return {
        "msg": NormalMessage(
            "",
            fields=(
                ("Timezone", f"`{profile.timezone}`"),
                ("Time Format", f"`{profile.time_format}`"),
                ("Cooldown Multiplier", f"`{profile.cooldown_multiplier}`"),
                ("Notications Enabled", notifications),
            ),
        )
    }


@register({"notify", "n", "all", *CoolDown.COOLDOWN_MAP.keys()})
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
        • `guild`
        • `pet`
    """
    print(tokens)
    if (tokens[0] in CoolDown.COOLDOWN_MAP or tokens[0] == "all") and tokens[-1] in {"on", "off"}:
        # allow implicit invocation of notify
        tokens = ["notify", *tokens]
        # make sure all passed tokens are valid cooldown type
        for token in {*tokens[1:-1]}:
            if token not in CoolDown.COOLDOWN_MAP and token != "all":
                return {"error": 1}
    # pass on to the toggle command
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


@register({"on", "off"})
def toggle(client, tokens, message, server, profile, msg, help=None):
    """
    Toggle your profile notifications **{version}**. Example:
      • `rcd {version}`
    """
    on_or_off = tokens[0]
    if help and len(tokens) == 1:
        return {"msg": HelpMessage(toggle.__doc__.format(version=on_or_off))}
    elif len(tokens) != 1:
        return {"error": 1}

    profile.update(notify=on_or_off == "on")
    return {"msg": SuccessMessage(f"Notifications are now **{on_or_off}** for **{message.author.name}**.")}


@register({"timezone", "tz"})
def timezone(client, tokens, message, server, profile, msg, help=None):
    """
    Set your timezone. Example:
        • `rcd timezone <timezone>` Sets your timezone to the provided timzone.
          (This only effects the time displayed in `rcd cd`; notification functionality
          is not effected.)
        • `rcd tz default` Sets your timezone back to the default.
    """
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


@register({"timeformat", "tf"})
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


@register({"multiplier", "mp"})
def multiplier(client, tokens, message, server, profile, msg, help=None):
    """
    Set a multiplier on your cooldowns to extend or reduce their frequency.
    E.g. if you are a tier 3 donator, you may want to set your multipler
    to `0.65`.

    Usage:
        • `rcd multiplier|mp <multiplier>`
    Examples:
        • `rcd multiplier 0.65`
        • `rcd mp 0.85`
        • `rcd mp default` Restore your multiplier to the default (`None`).

    Multipliers must be from [0 to 10).
    """
    command = tokens[0]
    if help or len(tokens) == 1:
        return {
            "msg": HelpMessage(
                multiplier.__doc__, fields=[("Info", f"Your current multiplier is `{profile.cooldown_multiplier}`")]
            )
        }
    elif len(tokens) != 2:
        return {
            "msg": ErrorMessage(
                f"Could not parse `rcd {command} {' '.join(tokens)}` as a valid multiplier "
                f"command; your input has more arguments that expected."
            )
        }
    if tokens[1] == "default":
        profile.cooldown_multiplier = None
    else:
        try:
            profile.cooldown_multiplier = decimal.Decimal(tokens[1])
        except:  # noqa
            return {
                "msg": ErrorMessage(
                    f"Could not parse `{tokens[1]}` as a valid multiplier; must be a decimal number or `default`."
                )
            }
    try:
        profile.full_clean()
    except ValidationError as e:
        return {"msg": ErrorMessage(f"Could not validate your multiplier; err={e.args[0]['cooldown_multiplier'][0]}.")}
    except Exception as e:
        return {"msg": ErrorMessage(f"Could not validate your multiplier for unknown reasons :(; err={e}.")}
    profile.save()
    return {"msg": SuccessMessage(f"Your Cooldown Multiplier is now `{tokens[1]}`.")}


@register({"whocan", "w"})
def whocan(client, tokens, message, server, profile, msg, help=None):
    """
    Determine who in your server can use a particular command. Example:
      • `rcd whocan dungeon`
      • `rcd w dungeon`
    """
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
        cooldown_type = cooldown_type_func("")

    ats = [
        f"<@{uid}>"
        for uid in set(
            Profile.objects.exclude(uid=profile.uid)
            .filter(
                ~Q(cooldown__type=cooldown_type)
                | Q(cooldown__after__lte=datetime.datetime.now(tz=datetime.timezone.utc), cooldown__type=cooldown_type)
            )
            .filter(server_id=message.channel.guild.id)
            .values_list("uid", flat=True)
        )
    ]
    if ats:
        msg = f"All of these players can `{rpg_command}`: \n\n" + "\n\t".join(ats)
        msg += f"\n\nExample: \n\n```rpg {rpg_command} {' '.join(ats)}\n\n```"
        return {"msg": SuccessMessage(msg, title=f"They can **{rpg_command.title()}**")}
    return {"msg": NormalMessage("Sorry, no one can do that right now.")}


@register({"dibbs", "dibbs?", "d", "d?"})
def dibbs(client, tokens, message, server, profile, msg, help=None):
    """
    Call "dibbs" on the guild raid.
    Usage:
        • `rcd dibbs|d[?]`
    Example:
        • `rcd dibbs` Call dibbs on next guild raid
        • `rcd dibbs?` Find out if anyone has dibbs without claiming it
    """
    if help:
        return {"msg": HelpMessage(dibbs.__doc__)}

    if not profile.player_guild:
        return {"msg": ErrorMessage(":disappointed: You aren't part of a guild.")}
    tz, tf = pytz.timezone(profile.timezone), profile.time_format
    after_message = (
        f" at `{profile.player_guild.after.astimezone(tz).strftime(tf)}`" if profile.player_guild.after else ""
    )
    raid_dibbs = profile.player_guild.raid_dibbs
    if tokens[0][-1] == "?":
        if raid_dibbs:
            player_with_dibbs = client.get_user(int(raid_dibbs.uid))
            return {"msg": NormalMessage(f"**{player_with_dibbs}** has dibbs on the next guild raid{after_message}.")}
        else:
            return {"msg": NormalMessage(f"No one has dibbs on the next guild raid{after_message}.")}
    if not raid_dibbs:
        profile.player_guild.update(raid_dibbs=profile)
        return {
            "msg": SuccessMessage(f"Okay! You've got dibbs on the next guild raid{after_message}!", title="Dibbsed!")
        }
    elif raid_dibbs == profile:
        return {
            "msg": NormalMessage(f"You've already got dibbs on the next guild raid{after_message}!", title="Dibbsed!")
        }
    else:
        player_with_dibbs = client.get_user(int(raid_dibbs.uid))
        return {"msg": NormalMessage(f"Sorry, **{player_with_dibbs}** already has dibbs.", title="Not this time!")}


@register(
    {
        "gambling": ("gambling", "g"),
        "g": ("gambling", "g"),
        "drops": ("drops", "dr"),
        "dr": ("drops", "dr"),
        "hunts": ("hunts", "hu"),
        "hu": ("hunts", "hu"),
    }
)
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
    long, short = stats.entry_tokens[tokens[0]]
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
                    f"Example usage: `rcd {short} 5 @player`",
                    title="Stats Usage Error",
                )
            }
    uid = None if _all else profile.uid
    # show all for an individual regardless of which server,
    # but if _all=True then we want to restrict to current server
    server_id = server.id if _all else None
    name = server.name if _all else client.get_user(int(profile.uid)).name
    if long == "gambling":
        return {
            "msg": NormalMessage(
                "", fields=Gamble.objects.stats(uid, minutes, server_id), title=f"{name}'s Gambling Addiction"
            )
        }
    elif long == "hunts":
        return {
            "msg": NormalMessage("", fields=Hunt.objects.hunt_stats(uid, minutes, server_id), title=f"{name}'s Carnage")
        }
    elif long == "drops":
        return {
            "msg": NormalMessage("", fields=Hunt.objects.drop_stats(uid, minutes, server_id), title=f"{name}'s Drops")
        }


@register({"admin"}, protected=True)
def admin(client, tokens, message, server, profile, msg, help=None):
    """
    Commands only available to administrative users. Use `rcd help admin [command]` for usage.
    • `rcd admin event`
    • `rcd admin scrape`
    """
    if len(tokens) > 1:
        return {"tokens": tokens[1:]}
    elif help:
        return {"msg": HelpMessage(admin.__doc__, title="Admin Help")}


@register({"event"}, protected=True)
def event(client, tokens, message, server, profile, msg, help=None):
    """
    Create and activate an event that has cooldown modifications. This will be active
    for all users.
    Usage:
    • `rcd admin event upsert|show|delete "NAME" [param=value {param=value ...}]`
    • `rcd admin event show NAME`
    Example:
        The below command will create or update the event XMAS 2020 to start at `2020-12-01T00:00:00` UTC,
        end at `2020-01-01T00:00:00` UTC, and have cooldown for arena as 7200 seconds for the duration.
        • `rcd admin event upsert "XMAS 2020" start=2020-12-01T00:00:00 end=2020-01-01T00:00:00 arena=60*60*12`
    """
    if help or len(tokens) < 3 or tokens[1] not in {"upsert", "show", "delete"}:
        return {"msg": HelpMessage(event.__doc__, title="Admin Event Help")}
    if tokens[1] == "upsert":
        if len(tokens) > 3:
            _event = Event.parse_event(tokens[3:], tokens[2])
            try:
                _event.save()
            except Exception as e:
                return {"msg": ErrorMessage(f"Encountered error executing command` {' '.join(tokens)}`; err = {e}")}
        else:
            return {
                "msg": ErrorMessage(
                    f'`rcd admin event {tokens[1]} "{tokens[2]}"` could not be parsed as a valid command. '
                    "Did you provide all required arguments?"
                )
            }
    elif tokens[1] == "delete":
        _event = Event.parse_event([], tokens[2])
        try:
            _event.delete()
            return {"msg": SuccessMessage(f'Event "{tokens[2]}" successfully deleted.', title="Delete Success")}
        except Exception as e:
            return {"msg": ErrorMessage(f"Encountered error executing command` {' '.join(tokens)}`; err = {e}")}
    else:
        _event = Event.parse_event([], tokens[2], upsert=False)
    fields = [
        (
            "Effective (UTC)",
            f'{_event.start.strftime("%Y-%m-%dT%H:%M")} to {_event.end.strftime("%Y-%m-%dT%H:%M")}',
        ),
    ]
    if _event.cooldown_adjustments:
        adj = _event.cooldown_adjustments
        fields.append(("Cooldowns (in Seconds)", "\n".join([f"{k:25} => {adj[k]:15}" for k in adj.keys()])))
    return {"msg": NormalMessage("", title=f'{tokens[1]} "{tokens[2]}"', fields=fields)}


@register({"scrape"}, protected=True)
def scrape(client, tokens, message, server, profile, msg, help=None):
    """
    Scrape the contents of this channel for future refence.
    Usage:
        • `rcd admin scrape [limit]`
    """
    if help:
        return {"msg": HelpMessage(scrape.__doc__)}
    limit = None
    if len(tokens) > 1:
        if not tokens[-1].isdigit() and not tokens[-1] == "all":
            return {"msg": ErrorMessage(f"scrape limit must be an integer, got {tokens[-1]}.")}
        elif tokens[-1].isdigit():
            limit = tokens[-1]
    channels = [client.get_channel(c.id) for c in Channel.objects.all()] if "all" in tokens else None
    scope = "all" if not limit else f"last {limit}"
    if channels:

        async def _scrape_channels():
            files, elapsed = await scrape_channels(channels, limit)
            newline = "\n"
            return SuccessMessage(
                f"Scrape completed in {elapsed} seconds.",
                title="Scrape Completed.",
                fields=(("Files", f"The following files were generated: ```\n{newline.join(files)}\n```"),),
            )

        return {
            "msg": SuccessMessage(f"Beginning Scrape of {scope} messages in all known channels."),
            "coro": (_scrape_channels, ()),
        }
    else:

        async def _scrape_channel():
            start = int(time.time())
            file = f"/tmp/{start}_{message.channel.id}_dump.json"
            file, elapsed = await scrape_channel(message.channel, start, file, limit)
            return f"<@!{message.author.id}> Your scrape has completed after {elapsed:,} seconds. Results in `{file}`."

        return {
            "msg": SuccessMessage(f"Beginning Scrape of {scope} messages in this channel."),
            "coro": (_scrape_channel, ()),
        }


@register(protected=True)
def _import(client, tokens, message, server, profile, msg, help=None):
    pass
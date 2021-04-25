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
from epic.crafting import Inventory, Items
from epic.crafting.recipes import full_index, full_map
from epic.models import Channel, CoolDown, Profile, Server, JoinCode, Gamble, Hunt, Event, Sentinel
from epic.utils import tokenize, to_human_readable
from epic.types.classes import ErrorMessage, NormalMessage, HelpMessage, SuccessMessage
from epic.history.scrape import scrape_channels, scrape_channel


register = default_registry


@register({"h", "help"})
def _help(client, tokens, message, server, profile, msg, help=None):
    """
        # EPIC Helper Bot Help
        You can use `rcd help` on any command to see its usage.

        ## Examples
    ```
    rcd help logs
    rcd h join
    rcd h whocan
    rcd h stats gambling
    ```

        ## Available Commands
            • `help`, `h`: Get help with any command
            • `join`, `register`: Register your server with the bot
            • `profile`, `p`: Manage or view your profile
            • `notify`: Manage your notification settings
            • `cd`, `rd` (or just `rcd` and `rrd`): View EPIC Helper Bot's record of your cooldowns
            • `whocan`, `w`: Ask "who can do this command right now?"
            • `dibbs`, `d`: Claim dibbs on the next guild raid
            • `stats`, `s`: View stats about your gameplay that EPIC Helper Bot has collected
            • `logs`: Calculate the future log-value of your inventory
            • `craft`, `c`: Ask "can I craft this recipe?"
            • `howmany`, `hm`: Ask "how many of this recipe can I craft?"
            • `info`, `i`: Information on various topics relating to the bot
    """
    if len(tokens) == 1:
        return {
            "msg": HelpMessage(
                _help.__doc__,
            )
        }
    return {"help": True, "tokens": tokens[1:]}


@register(
    entry_tokens={"", "cd", "rd", *CoolDown.COOLDOWN_MAP.keys()},
    param_filters=[lambda p: p.tokens[-1] not in {"on", "off"}],
)
def cd(client, tokens, message, server, profile, msg, help=None):
    """
        # EPIC Helper Cooldowns
        Display when your cooldowns are expected to be done.
        ## Usage
            • `rcd cd [<cooldown_types>]` shows all cooldowns
            • `rcd rd [<cooldown_types>]` shows ready cooldowns
        ## Examples
    ```
    rcd
    rcd cd
    rrd
    rcd rd
    rcd daily weekly
    ```
    """
    if help:
        return {"msg": HelpMessage(cd.__doc__)}

    if tokens[0] not in {"cd", "rd"}:
        # allow for implicit or default invocation of rcd
        tokens = ["cd", *tokens[1:]] if tokens[0] == "" else ["cd", *tokens]
    nickname = message.author.name
    cooldown_filter = lambda x: True  # show all filters by default

    if len(tokens) > 1:
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


@register({"info", "i"})
def info(client, tokens, message, server, profile, msg, help=None):
    """
        # Info Help
        Info about the bot and other supported topics.
        Note: This command is in early development and the invocation format is likely to change.

        ## Topics
        • `0`, `cooldown mechanics`: Detailed EPIC Rpg Helper cooldown mechanics
        • `1`, `default cooldowns`: EPIC Rpg's default cooldowns for all commands
        • `2`, `global cooldowns`: EPIC Rpg Helper's active global cooldowns
        • `3`, `my cooldowns`: My current calculated cooldown durations

        ## Usage
        • `rcd info|i <topic>|<topic number>`

        ## Examples
    ```
    rcd info 1
    rcd info default cooldowns
    ```
    """
    if help or len(tokens) == 1:
        return {"msg": HelpMessage(info.__doc__)}
    topic = " ".join(tokens[1:])
    if topic in {"bot", "0"}:
        return {
            "msg": NormalMessage(
                """
            # Cooldown Calculations
            Cooldowns are determined in various ways which depend on how EPIC Rpg responds to your commands.

            ## Normal Cooldown Calculation
            «If EPIC Rpg Helper determines that you have used a a valid command, it will attempt to calculate your new
            cooldown duration for that command, taking into account any active global events and any active
            multipliers you may have (see `rcd h multiplier`).»

            «In most cases, EPIC Rpg will respond with a standard cooldown response to tell you
            exactly how long it will be before you can use the command again. EPIC Rpg Helper will
            read this respond and schedule a notification based on it.»

            ## Group Cooldowns
            «For commands involving one or more people, EPIC Rpg Helper must also watch for EPIC Rpg reponses
            to determine whether a group command completed successfully and thus will go on cooldown as a result.»

            ## Pet Cooldowns
            «Because it is impossible to definitively determine who a pet cooldown response is for,
            EPIC Rpg Helper does not attempt to use the cooldown response to schedule a notification.
            Instead, it relies on the player to open their pet screen. It will schedule a notification for the
            pet which will return soonest according to the last pet screen it saw.»
            """
            )
        }

    cooldown_map = CoolDown.COOLDOWN_MAP.copy()
    format, output = "{:>1}d {:>02}h {:02}m {:02}s", ""
    if topic in {"default cooldowns", "1"}:
        title = "EPIC RPG Default Cooldowns"
        for key, delta in sorted(cooldown_map.items(), key=lambda x: x[1]):
            output += f"{key:12} => {format.format(*to_human_readable(delta))}\n"
        return {"msg": NormalMessage(f"```{output}```", title=title)}
    if topic in {"global cooldowns", "2"}:
        title = "Global Cooldowns, Including Event Data"
        cooldown_map = CoolDown.get_event_cooldown_map()
        for key, delta in sorted(cooldown_map.items(), key=lambda x: x[1]):
            output += f"{key:12} => {format.format(*to_human_readable(delta))}\n"
        return {"msg": NormalMessage(f"```{output}```", title=title)}
    elif topic in {"my cooldowns", "3"}:
        title = "My Cooldowns, Including Event Data and Multipliers"
        cooldown_map = CoolDown.get_event_cooldown_map()
        mp = profile.cooldown_multiplier
        for key, delta in sorted(cooldown_map.items(), key=lambda x: x[1]):
            delta = CoolDown.apply_multiplier(mp, delta, key) if mp else delta
            output += f"{key:12} => {format.format(*to_human_readable(delta))}\n"
        return {"msg": NormalMessage(f"```{output}```", title=title)}
    return {"msg": ErrorMessage(f"No such topic `{topic}`. ", title="Info Error")}


@register({"register", "join"})
def _register(client, tokens, message, server, profile, msg, help=None):
    """
    # EPIC Helper Registration Help
    «Register your server for use with Epic Reminder. This extra step is required to prevent general abuse of the bot.
    If you ask for a join code, I will probably give you one.»

    ## Usage
        • `rcd register|join <join_code>`

    ## Example
        • `rcd register asdf` attempts to register the server using the join code `asdf`
    """
    if help or len(tokens) == 1:
        return {"msg": HelpMessage(_register.__doc__)}
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
    #Profile Help
    «When called without any arguments, e.g. `rcd profile` this will display profile-related information.
    Otherwise, it will treat your input as a profile related sub-command.»


    ## Sub Commands
        • `timezone`, `tz`: Set the timezone information for your profile
        • `timeformat`, `tf`: Set the date and time formatting for your profile
        • `multiplier`, `mp`: Reduce or increase your cooldown durations
        • `notify`, `n`: Set which cooldowns the bot will notify you for

    ## Examples
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
            *timezone.entry_tokens,
            *timeformat.entry_tokens,
            *multiplier.entry_tokens,
            *notify.entry_tokens,
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


@register(
    entry_tokens={"notify", "n", "all", *CoolDown.COOLDOWN_MAP.keys()},
    param_filters=[lambda p: p.tokens[-1] in {"on", "off"} or p.help],
)
def notify(client, tokens, message, server, profile, msg, help=None):
    """
    «Manage your notification settings. Here you can specify which types of
    epic rpg commands you would like to receive reminders for. For example, you can
    enable or disable showing a reminder for when `rpg hunt` should be available. All reminders
    are enabled by default»

    ## Examples
        • `rcd notify on`, `rcd notify off`: Toggle the notification feature
        • `rcd notify hunt on`: Enable cd notifications for `rpg hunt`.
        • `rcd daily on`: Enable cd notifications for `rpg daily`.
        • `rcd n hunt off`: Enable notifications for `rpg hunt`
        • `rcd n weekly on`: Enable notifications for `rpg weekly`
        • `rcd n all off`: Disable all notification types (distinct from `rcd notify off`)

    ## Command Types
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
    if help:
        return {"msg": HelpMessage(notify.__doc__)}

    toggle_all = False
    # allow implicit invocation of notify
    tokens = tokens[1:] if tokens[0] in {"notify", "n"} else tokens
    # make sure all passed tokens are valid cooldown type
    command_types, toggle = tokens[:-1], tokens[-1]
    for command_type in command_types:
        if command_type not in CoolDown.COOLDOWN_MAP:
            if command_type != "all":
                return {"error": 1}
            toggle_all = True

    # invocation of the toggle command
    if len(tokens) == 1:
        return {"tokens": [toggle]}

    on = toggle == "on"
    if toggle_all:
        kwargs = {command_name: on for command_name, _ in CoolDown.COOLDOWN_TYPE_CHOICES}
    else:
        kwargs = {command_type: on for command_type in command_types}
    profile.update(last_known_nickname=message.author.name, **kwargs)
    notification_type_string = ", ".join(kwargs.keys())
    if not profile.notify:
        return {
            "msg": NormalMessage(
                f"Notifications for `{notification_type_string}` are now {toggle} for **{message.author.name}** "
                "but you will need to turn on notifications before you can receive any. "
                "Try `rcd on` to start receiving notifications."
            )
        }
    return {
        "msg": SuccessMessage(
            f"Notifications for **{notification_type_string}** are now **{toggle}** for **{message.author.name}**."
        )
    }


@register({"on", "off"})
def _toggle(client, tokens, message, server, profile, msg, help=None):
    """
    # Toggle Help
    Toggle your profile notifications **{version}**.

    ## Example
      • `rcd {version}`
    """
    on_or_off = tokens[0]
    if help and len(tokens) == 1:
        return {"msg": HelpMessage(_toggle.__doc__.format(version=on_or_off))}
    elif len(tokens) != 1:
        return {"error": 1}

    profile.update(notify=on_or_off == "on")
    return {"msg": SuccessMessage(f"Notifications are now **{on_or_off}** for **{message.author.name}**.")}


@register({"timezone", "tz"})
def timezone(client, tokens, message, server, profile, msg, help=None):
    """
    # Timezone Help
    Set your timezone. This only effects the time displayed in `rcd cd`; notification functionality is not effected.

    ## Usage
        • `rcd timezone <timezone>`: Sets your timezone to the provided timezone
    ## Examples
        • `rcd timezone America/Chicago`: Sets your timezone to America/Chicago
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
    # Time Format Help
    «Set the time format for the output of `rcd` using Python
    `strftime` notation. Defaults to `%I:%M:%S %p, %m/%d`. If
    you don't know what that means, see the linked resource below.»

    ## Usage
        • `rcd timeformat|tf "<format_string>"`
    ##Examples
        • `rcd timeformat "%I:%M:%S %p, %m/%d"` **Notice the quotes.** Very important!
        • `rcd tf "%Y-%m-%d %H:%M:%S"`
        • `rcd tf default` Restore your time format to default.
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
        # Multiplier Help
        «Set a multiplier on your cooldowns to extend or reduce their frequency.
        E.g. if you are a tier 3 donator, you may want to set your multiplier
        to `0.65`.»

        Multipliers must be from [0 to 10).

        ## Usage
            • `rcd multiplier|mp <multiplier>`
        ## Examples
    ```
    rcd multiplier 0.65
    rcd mp 0.85
    rcd mp default
    ```
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
    # Whocan Help
    Determine who in your server can use a particular command.

    ## Examples
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
    # Dibbs Help
    «Call "dibbs" on the next guild raid. To register your guild with EPIC Rpg Helper, you can run
    `rcd list`.»

    ## Usage
        • `rcd dibbs|d[?] [undo]`

    ## Examples
        • `rcd dibbs` Call dibbs on next guild raid
        • `rcd dibbs undo` Undo your dibbs call
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
    if len(tokens) > 1 and tokens[1] == "undo":
        if not raid_dibbs or profile.uid != raid_dibbs.uid:
            return {
                "msg": NormalMessage(
                    f"Well, you never actually had dibbs, " f"but at least now everyone knows you didn't want it."
                )
            }
        profile.player_guild.update(raid_dibbs=None)
        return {"msg": SuccessMessage(f"Great! No more dibbs for you!", title="Undibbsed!")}

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


@register({"logs", "log"})
def logs(client, tokens, message, server, profile, msg, help=None):
    """
    # Logs Help
    Ask for the future log value of your current inventory!

    «You may need to know how many logs you will have in A10 before you can decide whether
    you should progress to the next area. This command will tell you how many logs you
    will have in area 10 based on your current inventory.»

    The command assumes you are in A5 if no area is provided.

    ## Usage
        • `rcd logs [a{n}=a5] [@player=@you]`

    ## Examples
        • `rcd logs` assuming that I am in A5, how many logs am I gonna have in A10?
        • `rcd logs a7` now that I am in A7, how many logs am I gonna have in A10?
        • `rcd logs @kevin` how many logs is Kevin gonna have in area A10?

    """
    if help or not tokens:
        return {"msg": HelpMessage(logs.__doc__)}

    full_message, metadata = " ".join(tokens), {"area": 5}
    area_indicator = re.search(r" [aA](\d{1,2})", full_message)
    if area_indicator:
        area = int(area_indicator.groups()[0])
        start, end = area_indicator.span()
        tokens, metadata["area"] = tokenize(f"{full_message[0:start]}{full_message[end:]}"), area
    if not 1 <= metadata["area"] <= 15:
        return {"msg": ErrorMessage("Only areas 1-15 are valid!", title="Logs Error")}

    mentioned_profile = Profile.from_tag(tokens[-1], client, server, message)
    if mentioned_profile:
        profile, metadata["snoop"] = mentioned_profile, profile.uid

    open_sentinels = list(Sentinel.objects.filter(trigger=0, profile=profile, action="logs"))
    len(open_sentinels) == 0 and Sentinel.objects.create(trigger=0, profile=profile, action="logs", metadata=metadata)
    for sentinel in open_sentinels:
        sentinel.metadata.get("snoop", -1) == metadata.get("snoop", -1) and sentinel.update(metadata=metadata)

    _area = f'Area {metadata["area"]}'
    if metadata.get("snoop", None):
        return {
            "msg": NormalMessage(
                "Busybody, eh? Okay, I'll check next time they open their inventory.", title=f"Snoop Lawgs ({_area})"
            )
        }
    return {
        "msg": NormalMessage(
            "Okay, the next time I see your inventory, I'll say how many logs you should have in Area 10.",
            title=f"Logs ({_area})",
        )
    }


@register({"craft", "c"})
def craft(client, tokens, message, server, profile, msg, help=None):
    """
    # Craft Help
    Ask whether you can craft the given recipe!

    By default, the command assumes you are in A5.

    ## Usage
        • `rcd c|craft list gear|food [a{0-15}=a5] [@player=@you]`
        • `rcd c|craft <recipe_name>|<recipe_number> [a{0-15}=a5] [@player=@you]`
    ## Example
        • `rcd craft list gear` Show the list of available gear recipes
        • `rcd c 1 a3` Can I craft the wooden sword given that I'm in A3?
        • `rcd craft a5 ruby sword` Can I craft the ruby sword now that I'm in A5?
    """
    if help or not tokens:
        return {"msg": HelpMessage(craft.__doc__)}

    _original_tokens = [*tokens]
    tokens = tokens[1:]
    full_message, target, metadata = " ".join(tokens), "", {"area": 5}
    area_indicator = re.search(r"[aA](\d{1,2})", full_message)
    if area_indicator:
        area = int(area_indicator.groups()[0])
        start, end = area_indicator.span()
        tokens, metadata["area"] = tokenize(f"{full_message[0:start]}{full_message[end:]}"), area
        if not 1 <= metadata["area"] <= 15:
            return {"msg": ErrorMessage("Only areas 1-15 are valid!", title="Craft Error")}
        full_message = " ".join(tokens)

    target_indicator = re.search(r"(list)? ?(food|gear)? ?([\w\- ]+|\d{1,2})?", full_message)
    should_list, recipe_type, target = target_indicator.groups()
    if should_list and not recipe_type:
        tokens = tokens[1:] if should_list else tokens
        return {
            "msg": ErrorMessage(
                "Incorrect usage; expected a recipe type, got: " f"`{' '.join(tokens)}`", title="Recipe Error"
            )
        }
    elif not should_list and not target:
        return {"msg": ErrorMessage(f"You must provide a target, e.g.: `craft 1`", title="Recipe Error")}

    if should_list:
        recipe_list = "\n".join(
            [f"{number + 1:>2} => {name.replace('_', ' '):<15}" for number, name in full_index[recipe_type].items()]
        )
        return {"msg": NormalMessage(f"```{recipe_list}```", title="Recipe List")}
    elif target:
        target = full_index.get(int(target) - 1, "") if target.isdigit() else re.sub(r"[^\w]+", "_", target)

    if target not in full_map:
        return {"msg": ErrorMessage(f"No such recipe `{target}`", title="Craft Error")}
    metadata.update({"recipe": full_map[target].to_dict(), "name": target})

    mentioned_profile = Profile.from_tag(tokens[-1], client, server, message)
    if mentioned_profile:
        profile, metadata["snoop"] = mentioned_profile, profile.uid

    open_sentinels = list(Sentinel.objects.filter(trigger=0, profile=profile, action="can_craft"))
    len(open_sentinels) == 0 and Sentinel.objects.create(
        trigger=0, profile=profile, action="can_craft", metadata=metadata
    )
    for sentinel in open_sentinels:
        sentinel.metadata.get("snoop", -1) == metadata.get("snoop", -1) and sentinel.update(metadata=metadata)

    _area = f'Area {metadata["area"]}'
    if metadata.get("snoop", None):
        return {
            "msg": NormalMessage(
                "Busybody, eh? Okay, I'll check next time they open their inventory.", title=f"Snoop Craft ({_area})"
            )
        }
    return {
        "msg": NormalMessage(
            "Okay, the next time I see your inventory, "
            f"I'll say whether you can craft `{target.replace('_', ' ')}`.",
            title=f"Can Craft ({_area})",
        )
    }


@register({"howmany", "hm"})
def how_many(client, tokens, message, server, profile, msg, help=None):
    """
    # How Many Help
    Ask how many of the given recipe you can craft. By default, you are assumed to be in A5.

    ## Usage
        • `rcd hm|howmany <recipe_name>|<recipe_number>|<itemized recipe> [a{0-15}=a5] [@player=@you]`
    ## Examples
        • `rcd howmany fruit salad` How many fruit salads can I craft given that I'm in A5?
        • `rcd hm fruit salad a10` How many fruit salads can I craft given that I'm in A10?
        • `rcd hm apple=1 banana=1` How many times can I craft this custom recipe?
        • `rcd hm apple` How many apples can I craft?
    """
    if help or len(tokens) == 1:
        return {"msg": HelpMessage(how_many.__doc__)}

    _original_tokens = [*tokens]
    target, metadata, tokens = "", {"area": 5}, tokens[1:]
    mentioned_profile = Profile.from_tag(tokens[-1], client, server, message)
    if mentioned_profile:
        profile, metadata["snoop"] = mentioned_profile, profile.uid
        tokens = tokens[:-1]
    full_message = " ".join(tokens)

    area_indicator = re.search(r"[aA](\d{1,2})", full_message)
    if area_indicator:
        area = int(area_indicator.groups()[0])
        start, end = area_indicator.span()
        tokens, metadata["area"] = tokenize(f"{full_message[0:start]}{full_message[end:]}"), area
        if not 1 <= metadata["area"] <= 15:
            return {"msg": ErrorMessage("Only areas 1-15 are valid!", title="How Many Error")}
        full_message = " ".join(tokens)
    target_indicator, recipe_name = re.search(r"^\s*([\w\- ]+|\d{1,2})\s*$", full_message), "custom"
    if target_indicator:
        target = target_indicator.groups()[0]
        target = full_index.get(int(target) - 1, "") if target.isdigit() else re.sub(r"[^\w]+", "_", target)
        if target not in full_map:
            if target not in Items:
                return {"msg": ErrorMessage(f"No such recipe `{target}`", title="How Many Error")}
            # implicitly they have indicated that they want to know how many of an item they can have
            recipe = Inventory(**{target: 1})
        else:
            recipe = full_map[target]
        recipe_name = target
    else:
        items_list = re.findall(r"([\w\- ]+)=([1-9]+\d*)", full_message)
        try:
            recipe = Inventory(**{re.sub(r"[^\w]+", "_", item.strip()): int(qty) for item, qty in items_list})
        except AttributeError as e:
            return {
                "msg": ErrorMessage(
                    f"`{e.args[0]}` is not a valid item name. " f"Please remove any pluralization and try again.",
                    title="How Many Error",
                )
            }
    metadata.update({"recipe": recipe.to_dict(), "name": recipe_name})

    mentioned_profile = Profile.from_tag(tokens[-1], client, server, message)
    if mentioned_profile:
        profile, metadata["snoop"] = mentioned_profile, profile.uid

    open_sentinels = list(Sentinel.objects.filter(trigger=0, profile=profile, action="how_many"))
    len(open_sentinels) == 0 and Sentinel.objects.create(
        trigger=0, profile=profile, action="how_many", metadata=metadata
    )
    for sentinel in open_sentinels:
        sentinel.metadata.get("snoop", -1) == metadata.get("snoop", -1) and sentinel.update(metadata=metadata)

    _area = f'Area {metadata["area"]}'
    if metadata.get("snoop", None):
        return {
            "msg": NormalMessage(
                "Busybody, eh? Okay, I'll check next time they open their inventory.", title=f"Snoop How Many ({_area})"
            )
        }
    return {
        "msg": NormalMessage(
            "Okay, the next time I see your inventory, "
            f"I'll say how many of `{recipe_name}` you can craft.\n\n{recipe}",
            title=f"Can Craft ({_area})",
        )
    }


@register({"stats", "statistics", "s"})
def stats_namespace(client, tokens, message, server, profile, msg, help=None):
    """
        # Stats
        Show various stats that have been aggregated by the bot.

        ## Available SubCommands
        • `gambling`, `g`
        • `hunts`, `hu`
        • `drops`, `dr`

        ## Examples
    ```
    rcd help stats gambling
    rcd stats gambling
    rcd s g
    rcd g
    ```
    """
    if len(tokens) == 1:
        return {"msg": HelpMessage(stats_namespace.__doc__)}
    return {"tokens": tokens[1:]}  # pass along to the next step in the handler


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
    # Stats Help
    This command shows the output of {long} stats that the helper bot has managed to collect.

    ## Usage
        • `rcd {long}|{short} [num_minutes] [@player=@you]`

    ## Examples
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
    # Admin Help

    Commands only available to administrative users.

    ## Sub Commands:
        • `event`: Set global cooldown events
        • `scrape`: Scrape message history off of a channel (for debugging purposes)
    """
    if len(tokens) > 1:
        return {"tokens": tokens[1:]}
    elif help:
        return {"msg": HelpMessage(admin.__doc__, title="Admin Help")}


@register({"event"}, protected=True)
def event(client, tokens, message, server, profile, msg, help=None):
    """
        # Event Help
        Create and activate an event that has cooldown modifications. This will be active for all users.

        ## Usage
        • `rcd admin event upsert|show|delete "NAME" [param=value {param=value ...}]`
        • `rcd admin event show NAME`
        ## Example
        «The below command will create or update the event XMAS 2020 to start at `2020-12-01T00:00` UTC,
        end at `2020-01-01T00:00` UTC, and have cooldown for arena as 7200 seconds for the duration.»
    ```
    rcd admin event upsert "XMAS 2020" start=2020-12-01T00:00 end=2020-01-01T00:00 arena=60*60*12
    ```
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
        defaults, adj = CoolDown.COOLDOWN_MAP, _event.cooldown_adjustments
        output = "\n".join([f"{k:12}: {int(defaults[k].total_seconds()):8} => {adj[k]:8}" for k in adj.keys()])
        fields.append(("Cooldowns (in Seconds)", f"```{output}```"))
    return {"msg": NormalMessage("", title=f'{tokens[1]} "{tokens[2]}"', fields=fields)}


@register({"scrape"}, protected=True)
def scrape(client, tokens, message, server, profile, msg, help=None):
    """
    # Help Scrape
    Scrape the contents of this channel for future reference.

    ## Usage
        • `rcd admin scrape [limit]`
    ## Examples:
        • `rcd admin scrape all`: Scrape all contents in all known channels
        • `rcd admin scrape 10`: Scrape last 10 messages from this channel
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

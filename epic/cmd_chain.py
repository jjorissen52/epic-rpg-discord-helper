import datetime
import functools

from asgiref.sync import sync_to_async
from pipeline import execution_pipeline

from django.forms.models import model_to_dict

from epic.models import CoolDown, Profile, Server, JoinCode, get_instance, update_instance, upsert_cooldowns
from epic.utils import tokenize


class RpgCdMessage:
    def __init__(self, msg):
        self.msg = msg


class ErrorMessage(RpgCdMessage):
    pass


class NormalMessage(RpgCdMessage):
    pass


class SuccessMessage(RpgCdMessage):
    pass


def params_as_args(func):
    arg_names = ["tokens", "message", "server", "profile", "msg", "help"]

    @functools.wraps(func)
    def wrapper(params):
        if params["msg"] or params.get("error", None):
            # short-circuit to prevent running
            # the rest of the command chain
            return params
        # if they are using commands, we want to go ahead and
        # make them a profile.
        if params["profile"] is None:
            message, server = params["message"], params["server"]
            profile, _ = Profile.objects.get_or_create(
                uid=message.author.id,
                defaults={"last_known_nickname": message.author.name, "server": server, "channel": message.channel.id},
            )
            params["profile"] = profile
        args = [params.get(arg_name, None) for arg_name in arg_names]
        res = func(*args)
        if not res:
            return params
        params.update(res)
        return params

    return wrapper


@params_as_args
def _help(tokens, message, server, profile, msg, help=None, error=None):
    """
        Call `help` on an available command to see it's usage. Example:
        `rpgcd help register`

    Available Commands:
        - `rpgcd register`
        - `rpgcd on`
        - `rpgcd off`
        - `rpgcd profile`
        - `rpgcd notify <command_type> on|off`
        - `rpgcd cd`
    """
    if not tokens or (tokens[0] == "help" and len(tokens) == 1):
        return {"msg": NormalMessage(_help.__doc__)}
    if tokens[0] != "help":
        return
    return {"help": True, "tokens": tokens[1:]}


@params_as_args
def register(tokens, message, server, profile, msg, help=None, error=None):
    """
        Register your server for use with Epic Reminder.
    Compute resources are limited, so invite codes will be doled out sparingly.
    Example:
        `rpgcd register asdf`
    """
    if tokens[0] != "register":
        return None
    if help or len(tokens) == 1:
        return {"msg": NormalMessage(register.__doc__)}
    if server:
        return {"msg": NormalMessage(f"{message.channel.guild.name} has already joined! Hello again!")}
    if len(tokens) > 1:
        cmd, *args = tokens
    else:
        cmd, args = tokens[0], ()
    if not args:
        return {"msg": ErrorMessage("You must provide a join code to register.")}
    join_code = JoinCode.objects.filter(code=args[0], claimed=False).first()
    if not join_code:
        return {"msg": ErrorMessage("That is not a valid Join Code.")}
    server = Server.objects.create(id=message.channel.guild.id, name=message.channel.guild.name, code=join_code)
    join_code.claim()
    return {"msg": SuccessMessage(f"Welcome {message.channel.guild.name}!")}


@params_as_args
def notify(tokens, message, server, profile, msg, help=None):
    """
        Manage your notification settings. Here you can specify which types of
    epic rpg commands you would like to receive reminders for. For example, you can
    enable or disable showing a reminder for when `rpg hunt` should be available. All reminders
    are enabled by defailt. Example usage:
        - `rpgcd notify hunt on` Will turn on notifications when `rpg hunt` is off of cooldown.
        - `rpgcd notify hunt off` Will turn off notifications for `rpg hunt`
        - `rpgcd notify weekly on` Will turn on notifications for `rpg weekly`
        - `rpgcd notify all off` Will turn off all notifications (but `profile.notify == True`)

    Command Types:
        - `all`
        - `daily`
        - `weekly`
        - `lootbox`
        - `vote`
        - `hunt`
        - `adventure`
        - `training`
        - `duel`
        - `quest`
        - `work` (chop, mine, fish, etc.)
        - `horse`
        - `arena`
        - `dungeon`
    """
    if tokens[0] != "notify":
        return None
    if help or len(tokens) == 1:
        return {"msg": NormalMessage(notify.__doc__)}
    if len(tokens) != 3:
        return {"error": 1}
    _, command_type, toggle = tokens
    if command_type in CoolDown.COOLDOWN_MAP and toggle in {"on", "off"}:
        on = toggle == "on"
        # "work" is stored as "mine" in the database
        command_type = "mine" if command_type == "work" else command_type
        profile.update(**{command_type: on, "last_known_nickname": message.author.name})
        if not profile.notify:
            return {
                "msg": NormalMessage(
                    f"Notifications for `{command_type}` are now {toggle} for **{message.author.name}** "
                    "but you will need to turn on notifications before you can receive any. "
                    "Try `rpgcd on` to start receiving notifcations."
                )
            }
        return {
            "msg": SuccessMessage(
                f"Notifications for **{command_type}** are now **{toggle}** for **{message.author.name}**."
            )
        }


@params_as_args
def on(tokens, message, server, profile, msg, help=None):
    """
    Toggle your profile notifications **on**. Example:
    `rpgcd on`
    """
    if tokens[0] != "on":
        return None
    if help and len(tokens) == 1:
        return {"msg": NormalMessage(on.__doc__)}
    elif len(tokens) != 1:
        return {"error": 1}

    profile.update(notify=True)
    return {"msg": SuccessMessage(f"Notifications are now **on** for **{message.author.name}**.")}


@params_as_args
def off(tokens, message, server, profile, msg, help=None):
    """
    Toggle your profile notifications **off**. Example:
    `rpgcd off`
    """
    if tokens[0] != "off":
        return None
    if help and len(tokens) == 1:
        return {"msg": NormalMessage(off.__doc__)}
    elif len(tokens) != 1:
        return {"error": 1}

    profile.update(notify=False)
    return {"msg": SuccessMessage(f"Notifications are now **off** for **{message.author.name}**.")}


@params_as_args
def _profile(tokens, message, server, profile, msg, help=None):
    """
    Display your profile information. Example:
    `rpgcd profile`
    """
    if tokens[0] != "profile":
        return None
    if help and len(tokens) == 1:
        return {"msg": NormalMessage(_profile.__doc__)}
    elif len(tokens) != 1:
        return {"error": 1}
    msg = ""
    for k, v in model_to_dict(profile).items():
        if isinstance(v, bool):
            msg += f"`{k:12} => {'on ' if v else 'off'}`\n"
    return {"msg": NormalMessage(msg)}


@params_as_args
def cd(tokens, message, server, profile, msg, help=None):
    """
    Display when your cooldowns are expected to be done. Example:
    `rpgcd cd`
    """
    if tokens[0] != "cd":
        return None
    if help and len(tokens) == 1:
        return {"msg": NormalMessage(cd.__doc__)}
    elif len(tokens) != 1:
        return {"error": 1}
    msg = ""
    now, default = datetime.datetime.now(tz=datetime.timezone.utc), datetime.datetime(
        1790, 1, 1, tzinfo=datetime.timezone.utc
    )
    cooldowns = {_cd[0]: _cd[1] for _cd in CoolDown.objects.filter(profile_id=profile.pk).values_list("type", "after")}
    for cooldown_type, _ in CoolDown.COOLDOWN_TYPE_CHOICES:
        if cooldowns.get(cooldown_type, default) > now:
            msg += f"`{cooldown_type:12} {cooldowns[cooldown_type].strftime('%Y-%m-%d %H:%M')}`\n"
    return {"msg": NormalMessage(msg)}


command_pipeline = execution_pipeline(
    pre=[
        _help,
        register,
        notify,
        on,
        off,
        _profile,
        cd,
    ],
)


@sync_to_async
@command_pipeline
def handle_rpcd_message(tokens, message, server, profile, msg, help=None, error=None):
    if (error and not isinstance(error, str)) or not msg:
        return ErrorMessage(f"`rpgcd {' '.join(tokens)}` could not be parsed as a valid command.")
    elif error:
        return ErrorMessage(error)
    return msg

import functools
import re

from epic.models import Profile, Channel
from epic.utils import ErrorMessage


def init_registry(*wrappers):
    registry, admin_protected = [], {}
    help_tokens = {"h", "help"}

    def token_filter(func, acceptable_tokens, patterns=None, filter_funcs=None):
        patterns = [] if not patterns else patterns
        acceptable_tokens = set() if not acceptable_tokens else acceptable_tokens
        filter_funcs = [] if not filter_funcs else filter_funcs

        @functools.wraps(func)
        def filtered_command(client, tokens, *rest):
            entry_token = "" if not tokens else tokens[0]
            if filter_funcs and not any(f(tokens) for f in filter_funcs):
                return
            if entry_token not in acceptable_tokens and entry_token not in help_tokens:
                if not any(re.match(pattern, entry_token) for pattern in patterns):
                    return  # not an invocation of this command
            return func(client, tokens, *rest)

        return filtered_command

    def protect(func):
        @functools.wraps(func)
        def protected_command(client, tokens, message, server, profile, *args):
            if admin_protected[func.__name__] and not profile.admin_user:
                return {"msg": ErrorMessage("Sorry, only administrative users can use this command.")}
            return func(client, tokens, message, server, profile, *args)

        return protected_command

    def register(cmd=None, entry_tokens=None, entry_patterns=None, token_filters=None, protected=False, **kwargs):
        if entry_tokens is None:
            if not callable(cmd):
                entry_tokens = cmd

        def _register(_cmd):
            assert callable(_cmd), f"{_cmd.__name__} is not callable and cannot be registered as a command."
            if entry_tokens or entry_patterns or token_filters:
                _cmd = token_filter(_cmd, entry_tokens, entry_patterns, token_filters)
            if protected:
                admin_protected[_cmd.__name__] = True
                _cmd = protect(_cmd)
            for w in wrappers:
                _cmd = w(_cmd)
            _cmd.entry_tokens, _cmd.entry_patterns, _cmd.entry_filters = entry_tokens, entry_patterns, token_filters
            for key, value in kwargs.items():
                setattr(_cmd, key, value)
            registry.append(_cmd)
            return _cmd

        if callable(cmd):
            return _register(cmd)

        return _register

    register.registry = registry
    register.admin_protected = admin_protected
    return register


def params_as_args(func):
    arg_names = ["client", "tokens", "message", "server", "profile", "msg", "help"]

    @functools.wraps(func)
    def wrapper(params):
        if params["msg"] or params.get("error", None) or params.get("coro", None):
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
                # just keeping track of used channels
                _channel, _ = Channel.objects.get_or_create(
                    id=message.channel.id,
                    defaults={
                        "name_at_creation": message.channel.name,
                        "server_id": server.id,
                    },
                )
                params["profile"] = profile
            elif not help and tokens and tokens[0] not in {"help", "register"}:
                params["msg"] = ErrorMessage(
                    "You can only use `help` and `register` commands until "
                    f"{message.channel.guild.name} has used a join code."
                )
        # first token is empty string if there are no given tokens
        params["tokens"] = params["tokens"] if params["tokens"] else [""]
        args = [params.get(arg_name, None) for arg_name in arg_names]
        res = func(*args)
        if not res:
            return params
        params.update(res)
        return params

    return wrapper


default_registry = init_registry(params_as_args)

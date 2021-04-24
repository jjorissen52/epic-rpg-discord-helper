import datetime
import inspect
import re
import shlex
import operator
import functools
import sys
import traceback
from types import SimpleNamespace

import discord


class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


def tokenize(cmd, preserve_case=False):
    if not cmd:
        return cmd
    if not preserve_case:
        cmd = cmd.lower()
    return shlex.split(cmd)


def int_from_token(token):
    token = token.strip()
    if re.match(r"^([0-9\* ]+)$", token):
        int_tokens, prod = token.replace(" ", "").split("*"), 1
        prod = functools.reduce(operator.mul, [int(t) for t in int_tokens], 1)
        return prod
    elif token.isdigit():
        return int(token)


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


def to_human_readable(delta: datetime.timedelta):
    total_seconds = int(delta.total_seconds())
    seconds = total_seconds % 60
    minutes = (total_seconds % 3600 - seconds) // 60
    hours = (total_seconds % (3600 * 24) - minutes - seconds) // 3600
    days = (total_seconds - hours - minutes - seconds) // (3600 * 24)
    return days, hours, minutes, seconds


def defaults_from(dict_obj, defaults):
    return [dict_obj.get(key, defaults[key]) for key in defaults]


class Namespace(SimpleNamespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._empty = not args and not kwargs

    def __getattribute__(self, item):
        try:
            attr = super().__getattribute__(item)
        except AttributeError:
            return Namespace()
        if attr is None:
            return Namespace()
        return attr

    def __str__(self):
        if self._empty:
            return ""
        return "Namespace Obj"

    def __bool__(self):
        return not self._empty


def recursive_namespace(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = recursive_namespace(v)
        return Namespace(**obj)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = recursive_namespace(obj[i])
        return obj
    return obj


def ignore_broken_pipe(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BrokenPipeError:
            pass
        except SystemExit:
            raise
        except:  # noqa
            traceback.print_exc()
            exit(1)
        finally:
            try:
                sys.stdout.flush()
            finally:
                try:
                    sys.stdout.close()
                finally:
                    try:
                        sys.stderr.flush()
                    finally:
                        sys.stderr.close()

    # don't mask our function signature
    wrapper.__signature__ = inspect.signature(func)
    return wrapper

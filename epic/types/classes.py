from types import SimpleNamespace

import discord


class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


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
    color = 0xD703FC


class SuccessMessage(RCDMessage):
    color = 0x628F47


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

    @classmethod
    def from_collection(cls, obj):
        return _recursive_namespace(obj)


def _recursive_namespace(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = _recursive_namespace(v)
        return Namespace(**obj)
    elif isinstance(obj, (list, tuple)):
        for i in range(len(obj)):
            obj[i] = _recursive_namespace(obj[i])
        return obj
    return obj

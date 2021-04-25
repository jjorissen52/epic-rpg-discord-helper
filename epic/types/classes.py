import re
from types import SimpleNamespace

import discord

from epic.utils import defaults_from, remove_span, replace_span


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

    REGEXES = {
        "title": re.compile(r"\s*(?<!#)#\s*([^#\n]+)\n"),
        "fields": re.compile(r"\s*##\s*([^\n]+)\n([^#]*)"),
        "nobreak": re.compile(r"«([^»]*)»"),
    }

    def markup_pass(self, msg, title, footer, fields):
        title, fields = title, list(reversed(fields)) if fields else []
        for nobreak_match in reversed(list(self.REGEXES["nobreak"].finditer(msg))):
            # any text wrapped in "nobreak" indicators should have linebreaks removed
            nobreak_content = " ".join(self.REGEXES["nobreak"].sub("\1", nobreak_match.groups()[0]).split())
            msg = replace_span(msg, nobreak_content, nobreak_match.span())
        title_match = self.REGEXES["title"].search(msg)
        if title_match:
            title, msg = title_match.groups()[0], remove_span(msg, title_match.span())
        # go in reverse so the spans still point to valid indices as we iterate
        for field_match in reversed(list(self.REGEXES["fields"].finditer(msg))):
            section_name, section_content = field_match.groups()
            fields.append((section_name, section_content))
            msg = remove_span(msg, field_match.span())
        return {"msg": msg, "title": title, "fields": reversed(fields), "footer": footer}

    def __init__(self, msg, title=None, footer=None, fields=None):
        self.msg, self.title, self.footer, self.fields = defaults_from(
            self.markup_pass(msg, title, footer, fields),
            {
                "msg": msg,
                "title": title,
                "footer": footer,
                "fields": fields,
            },
        )

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

    def __init__(self, msg, title=None, footer=None, fields=None):
        super(HelpMessage, self).__init__(msg, title, footer, fields)


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

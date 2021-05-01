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
        "verbatim": re.compile(
            r"(?:[\t ]*)```([\w]+)?\n(.*)\n(?:[ \t]+)?```", re.DOTALL
        ),  # re.DOTALL makes .* match newlines
        "within_verbatim": re.compile(r"\s+([^\n]*)\n"),
    }

    def markup_pass(self, msg, title, footer, fields):
        title, fields = title, list(fields)[::-1] if fields else []
        # go in reverse so the spans still point to valid indices as we iterate
        for nobreak_match in list(self.REGEXES["nobreak"].finditer(msg))[::-1]:
            # any text wrapped in "nobreak" indicators should have linebreaks removed
            nobreak_content = " ".join(self.REGEXES["nobreak"].sub("\1", nobreak_match.groups()[0]).split())
            msg = replace_span(msg, nobreak_content, nobreak_match.span())
        title_match = self.REGEXES["title"].search(msg)
        if title_match:
            title, msg = title_match.groups()[0], remove_span(msg, title_match.span())
        for verbatim_match in list(self.REGEXES["verbatim"].finditer(msg))[::-1]:
            language, content = verbatim_match.groups()
            content = "\n".join(self.REGEXES["within_verbatim"].findall(f"{content}\n"))
            msg = replace_span(msg, f"```{language if language else ''}\n{content}\n```", verbatim_match.span())
        for field_match in list(self.REGEXES["fields"].finditer(msg))[::-1]:
            section_name, section_content = field_match.groups()
            # adding this character https://unicode-table.com/en/200B/ prevents the first item from being
            # de-dented ¯\_(ツ)_/¯
            section_content = f"\u200b{section_content}" if not section_content.startswith("```") else section_content
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

    def __call__(self, *args, **kwargs):
        raise Exception("Attempted call", args, kwargs)

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

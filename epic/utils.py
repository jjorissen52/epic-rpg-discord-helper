import re
import shlex
import operator
import functools

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
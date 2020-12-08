import re
import shlex
import operator
import functools


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

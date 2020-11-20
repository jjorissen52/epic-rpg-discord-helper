import re


class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


def tokenize(cmd):
    if not cmd:
        return cmd
    return re.sub(r"\s+", " ", cmd).strip().split()

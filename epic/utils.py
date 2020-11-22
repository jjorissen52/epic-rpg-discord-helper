import re


class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


def tokenize(cmd, preserve_case=False):
    if not cmd:
        return cmd
    cmd = re.sub(r"\s+", " ", cmd).strip()
    if not preserve_case:
        cmd = cmd.lower()
    return cmd.split()

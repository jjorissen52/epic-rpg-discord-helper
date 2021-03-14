import collections
import re
from types import SimpleNamespace
from typing import Tuple

FUTURE_AVAILABLE = True

try:
    import materials
except ImportError:

    def _(*args, **kwargs):
        return 0

    materials = SimpleNamespace(future=_)
    FUTURE_AVAILABLE = False


patterns = [
    re.compile(r"\*\*apple\*\*: (?P<apple>\d+)"),
    re.compile(r"\*\*banana\*\*: (?P<banana>\d+)"),
    re.compile(r"\*\*normie fish\*\*: (?P<normie_fish>\d+)"),
    re.compile(r"\*\*golden fish\*\*: (?P<golden_fish>\d+)"),
    re.compile(r"\*\*EPIC fish\*\*: (?P<epic_fish>\d+)"),
    re.compile(r"\*\*wooden log\*\*: (?P<wooden_log>\d+)"),
    re.compile(r"\*\*EPIC log\*\*: (?P<epic_log>\d+)"),
    re.compile(r"\*\*SUPER log\*\*: (?P<super_log>\d+)"),
    re.compile(r"\*\*MEGA log\*\*: (?P<mega_log>\d+)"),
    re.compile(r"\*\*HYPER log\*\*: (?P<hyper_log>\d+)"),
    re.compile(r"\*\*ULTRA log\*\*: (?P<ultra_log>\d+)"),
    # re.compile(r"\*\*wolf skin\*\*: (?P<wolf_skin>\d+)"),
    # re.compile(r"\*\*zombie eye\*\*: (?P<zombie_eye>\d+)"),
    # re.compile(r"\*\*unicorn horn\*\*: (?P<unicorn_horn>\d+)"),
    # re.compile(r"\*\*mermaid hair\*\*: (?P<mermaid_hair>\d+)"),
    # re.compile(r"\*\*chip\*\*: (?P<chip>\d+)"),
    # re.compile(r"\*\*dragon scale\*\*: (?P<dragon_scale>\d+)"),
]


def parse_inventory(*values):
    inventory = {
        "wooden_log": 0,
        "epic_log": 0,
        "super_log": 0,
        "mega_log": 0,
        "hyper_log": 0,
        "ultra_log": 0,
        "normie_fish": 0,
        "golden_fish": 0,
        "epic_fish": 0,
        "apple": 0,
        "banana": 0,
        "ruby": 0,
    }
    full_string = "\n".join(values)
    for pattern in patterns:
        match = pattern.search(full_string)
        if match:
            inventory.update(match.groupdict())
    return inventory


InventoryTuple = collections.namedtuple(
    "InventoryTuple",
    "wooden_log,epic_log,super_log,mega_log,hyper_log,ultra_log,"
    "normie_fish,golden_fish,epic_fish,"
    "apple,banana,"
    "ruby",
)


def calculate_future_logs(area: int, inventory: dict):
    return materials.future(area, *map(int, InventoryTuple(**inventory))), FUTURE_AVAILABLE


def calculate_log_future(area: int, *values: Tuple[str]):
    return calculate_future_logs(area, parse_inventory(*values))


if __name__ == "__main__":
    inventory = parse_inventory(
        "<:normiefish:697940429999439872> **normie fish**: 89"
        "\n<:goldenfish:697940429500317727> **golden fish**: 20\n"
        "<:EPICfish:543182761431793715> **EPIC fish**: 12\n<:woodenlog:770880739926999070> **wooden log**: 16376\n"
        "<:EPICwoodenlog:541056003517710348> **EPIC log**: 302\n<:SUPEREPICwoodenlog:541384398503673866> "
        "**SUPER log**: 38\n<:MEGASUPEREPICwoodenlog:545396411316043776> **MEGA log**: 6\n"
        "<:wolfskin:541384010690199552> **wolf skin**: 3\n<:zombieeye:542483215122694166> **zombie eye**: 3"
        "\n<:unicornhorn:545329267425149112> **unicorn horn**: 19"
        "\n<:dragonscale:619991355317289007> **dragon scale**: 3",
    )
    print(calculate_future_logs(5, inventory))

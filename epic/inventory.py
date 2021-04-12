import re
from typing import Tuple

from epic.crafting.recipes import full_map

FUTURE_AVAILABLE = True

try:
    from epic import crafting
except ImportError:
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
    re.compile(r"\*\*wolf skin\*\*: (?P<wolf_skin>\d+)"),
    re.compile(r"\*\*zombie eye\*\*: (?P<zombie_eye>\d+)"),
    re.compile(r"\*\*unicorn horn\*\*: (?P<unicorn_horn>\d+)"),
    re.compile(r"\*\*mermaid hair\*\*: (?P<mermaid_hair>\d+)"),
    re.compile(r"\*\*chip\*\*: (?P<chip>\d+)"),
    re.compile(r"\*\*dragon scale\*\*: (?P<dragon_scale>\d+)"),
    re.compile(r"\*\*common lootbox\*\*: (?P<common>\d+)"),
    re.compile(r"\*\*uncommon lootbox\*\*: (?P<uncommon>\d+)"),
    re.compile(r"\*\*rare lootbox\*\*: (?P<rare>\d+)"),
    re.compile(r"\*\*EPIC lootbox\*\*: (?P<epic>\d+)"),
    re.compile(r"\*\*EDGY lootbox\*\*: (?P<edgy>\d+)"),
    re.compile(r"\*\*OMEGA lootbox\*\*: (?P<omega>\d+)"),
    re.compile(r"\*\*GODLY lootbox\*\*: (?P<godly>\d+)"),
    re.compile(r"\*\*arena cookie\*\*: (?P<cookie>\d+)"),
]


def parse_inventory(*values):
    inventory = {}
    full_string = "\n".join(values)
    for pattern in patterns:
        match = pattern.search(full_string)
        if match:
            inventory.update(match.groupdict())
    return inventory


def calculate_log_future(area: int, *values: Tuple[str]):
    if not FUTURE_AVAILABLE:
        return 0, False
    return crafting.Inventory(area, **{name: int(qty) for name, qty in parse_inventory(*values).items()}).future(), True


def can_craft(area: int, type: str, recipe: str, *values: Tuple[str]):
    if not FUTURE_AVAILABLE:
        return False, False
    inventory = crafting.Inventory(area, **{name: int(qty) for name, qty in parse_inventory(*values).items()})
    return crafting.can_craft(full_map[type][recipe], inventory), True


if __name__ == "__main__":
    inventory = (
        "<:normiefish:697940429999439872> **normie fish**: 89"
        "\n<:goldenfish:697940429500317727> **golden fish**: 20\n"
        "<:EPICfish:543182761431793715> **EPIC fish**: 12\n<:woodenlog:770880739926999070> **wooden log**: 16376\n"
        "<:EPICwoodenlog:541056003517710348> **EPIC log**: 302\n<:SUPEREPICwoodenlog:541384398503673866> "
        "**SUPER log**: 38\n<:MEGASUPEREPICwoodenlog:545396411316043776> **MEGA log**: 6\n"
        "<:wolfskin:541384010690199552> **wolf skin**: 3\n<:zombieeye:542483215122694166> **zombie eye**: 3"
        "\n<:unicornhorn:545329267425149112> **unicorn horn**: 19"
        "\n<:dragonscale:619991355317289007> **dragon scale**: 3"
    )
    print(calculate_log_future(5, inventory))

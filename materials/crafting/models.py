from typing import Union

import materials


class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError(name)


item_names = [
    "wooden_log",
    "epic_log",
    "super_log",
    "mega_log",
    "hyper_log",
    "ultra_log",
    "normie_fish",
    "golden_fish",
    "epic_fish",
    "apple",
    "banana",
    "ruby",
    "common",
    "uncommon",
    "rare",
    "epic",
    "edgy",
    "omega",
    "godly",
    "cookie",
    "wolf_skin",
    "zombie_eye",
    "unicorn_horn",
    "mermaid_hair",
    "chip",
    "dragon_scale",
]

item_map = {name: idx for idx, name in enumerate(item_names)}

Items = Enum(item_names)


class Inventory:
    inventory = None
    area = None
    level = None

    def __init__(self, area=10, level=1, **kwargs):
        self.inventory = [0] * len(item_names)
        for item_name, qty in kwargs.items():
            idx = item_map[getattr(Items, item_name)]
            assert isinstance(qty, int)
            self.inventory[idx] = qty
        assert isinstance(area, int) and 1 <= area <= 15
        assert isinstance(level, int) and level > 0
        self.area = area
        self.level = level

    @classmethod
    def _get_idx(cls, key: Union[int, str]):
        return item_map[getattr(Items, key)] if isinstance(key, str) else key

    def __getitem__(self, item: Union[int, str]) -> int:
        return self.inventory[self._get_idx(item)]

    def __setitem__(self, key: Union[int, str], value: int):
        self.inventory[self._get_idx(key)] = value

    def __add__(self, other: "Inventory"):
        new = Inventory(area=self.area)
        for idx in range(len(self.inventory)):
            new[idx] = self.inventory[idx] + other.inventory[idx]
        return new

    def __mul__(self, other: int):
        assert other >= 0, "Can only multiply by 0+"
        new = Inventory(area=self.area)
        for _ in range(other):
            new = new + self
        return new

    def future(self):
        return materials.future(self.area, *self.inventory[:12])

    def to_dict(self):
        return {
            **{item_names[idx]: qty for idx, qty in enumerate(self.inventory)},
            "level": self.level,
            "area": self.area,
        }

    def __str__(self):
        string = "\n"
        non_zero = {item: self[item] for item in item_names if self[item]}
        if not non_zero:
            return ""
        max_name_length = max(map(len, non_zero))
        for item, qty in non_zero.items():
            string = f"{string}{item:>{max_name_length}}: {qty}\n"

        return f"```{string}```"

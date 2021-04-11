import materials


class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


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

    def __init__(self, area=10, **kwargs):
        self.inventory = [0] * len(item_names)
        for item_name, qty in kwargs.items():
            idx = item_map[getattr(Items, item_name)]
            assert isinstance(qty, int)
            self.inventory[idx] = qty
        assert isinstance(area, int) and 1 <= area <= 15
        self.area = area

    def future(self):
        return materials.future(self.area, *self.inventory[:12])

    def to_dict(self):
        return {item_names[idx]: qty for idx, qty in enumerate(self.inventory)}

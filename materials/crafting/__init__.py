from typing import Tuple, List

import materials
from . import recipes
from .models import Inventory


def can_craft(recipe: Inventory, inventory: Inventory) -> bool:
    return materials.can_craft(
        recipe.inventory,
        inventory.inventory,
        inventory.area,
    )


def how_many(recipe: Inventory, inventory: Inventory) -> Tuple[int, List[int]]:
    return materials.how_many(
        recipe.inventory,
        inventory.inventory,
        inventory.area,
    )

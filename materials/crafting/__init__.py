import materials
from .models import Inventory


def can_craft(recipe: Inventory, inventory: Inventory) -> bool:
    return materials.can_craft(
        recipe.inventory,
        inventory.inventory,
    )

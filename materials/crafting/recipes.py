from .models import Inventory

RUBY_SWORD = Inventory(wooden_log=400, mega_log=1, ruby=5)
EDGY_ARMOR = Inventory(wolf_skin=50, zombie_eye=50, unicorn_horn=50, mermaid_hair=35, chip=15)

recipe_map = {
    "ruby_sword": RUBY_SWORD,
    "edgy_armor": EDGY_ARMOR,
}

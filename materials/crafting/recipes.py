from .models import Inventory as _

WOODEN_SWORD = _(epic_log=1, wooden_log=15, level=1)
FISH_ARMOR = _(wooden_log=10, normie_fish=20, level=1)
FISH_SWORD = _(epic_log=5, golden_fish=20, level=2)
WOLF_ARMOR = _(wooden_log=120, epic_log=2, wolf_skin=2, level=4)
APPLE_SWORD = _(wooden_log=90, super_log=1, apple=70, level=4)
ZOMBIE_ARMOR = _(wooden_log=210, super_log=3, zombie_eye=1, level=6)
BANANA_ARMOR = _(wooden_log=350, super_log=8, banana=25, level=6)
RUBY_SWORD = _(wooden_log=400, mega_log=1, ruby=5, level=8)
EPIC_ARMOR = _(epic_log=125, epic_fish=1, level=8)
UNICORN_SWORD = _(super_log=8, normie_fish=500, unicorn_horn=6, level=11)
RUBY_ARMOR = _(super_log=12, mega_log=3, ruby=10, unicorn_horn=8, level=11)
HAIR_SWORD = _(mega_log=5, mermaid_hair=10, level=14)
# we just assume they have the money for now...
COIN_ARMOR = _(hyper_log=1, level=14)  # coins=654_321
COIN_SWORD = _(hyper_log=2, ruby=5, level=17)  # coins = 1234567
MERMAID_ARMOR = _(super_log=12, normie_fish=150, golden_fish=250, mermaid_hair=25, level=17)
ELECTRONICAL_SWORD = _(hyper_log=3, chip=15, level=20)
ELECTRONICAL_ARMOR = _(super_log=4, hyper_log=1, chip=20, level=20)
EDGY_SWORD = _(wooden_log=1000, ultra_log=1, level=50)
EDGY_ARMOR = _(wolf_skin=50, zombie_eye=50, unicorn_horn=50, mermaid_hair=35, chip=15, level=50)
ULTRA_EDGY_SWORD = _(ultra_log=1, epic_fish=1, dragon_scale=20, level=70)
ULTRA_EDGY_ARMOR = _(ultra_log=1, ruby=400, dragon_scale=40, level=70)
OMEGA_SWORD = _(mega_log=50, dragon_scale=50, level=100)
OMEGA_ARMOR = _(dragon_scale=50, omega=1, level=100)
ULTRA_OMEGA_SWORD = _(ultra_log=50, dragon_scale=100, level=200)
ULTRA_OMEGA_ARMOR = _(dragon_scale=400, level=200)  # life_potion=1
GODLY_SWORD = _(omega=15, godly=1, level=500)  # dragon_essence=10

BAKED_FISH = _(epic_log=12, golden_fish=12, epic_fish=1)
MUTANT_CREATURE = _(wolf_skin=3, zombie_eye=2, unicorn_horn=2, mermaid_hair=3)
FRUIT_SALAD = _(apple=25, banana=6)
APPLE_JUICE = _(apple=8, hyper_log=1)
SUPER_COOKIE = _(cookie=1000)

BANANA_PICKAXE = _(mega_log=6, banana=1)
HEAVY_APPLE = _(ruby=35, apple=1)
FILLED_LOOTBOX = _(apple=12, banana=8, cookie=25, rare=1)
COIN_SANDWICH = _(normie_fish=12, epic_fish=1, banana=2)  # coin=2
FRUIT_ICE_CREAM = _(super_log=1, apple=2, banana=1)

gear_recipe_map = {
    "wooden_sword": WOODEN_SWORD,
    "fish_armor": FISH_ARMOR,
    "fish_sword": FISH_SWORD,
    "wolf_armor": WOLF_ARMOR,
    "apple_sword": APPLE_SWORD,
    "zombie_armor": ZOMBIE_ARMOR,
    "banana_armor": BANANA_ARMOR,
    "ruby_sword": RUBY_SWORD,
    "epic_armor": EPIC_ARMOR,
    "unicorn_sword": UNICORN_SWORD,
    "ruby_armor": RUBY_ARMOR,
    "hair_sword": HAIR_SWORD,
    # we just assume they have the money for now...
    "coin_armor": COIN_ARMOR,  # coins=654_321
    "coin_sword": COIN_SWORD,  # coins = 1234567
    "mermaid_armor": MERMAID_ARMOR,
    "electronical_sword": ELECTRONICAL_SWORD,
    "electronical_armor": ELECTRONICAL_ARMOR,
    "edgy_sword": EDGY_SWORD,
    "edgy_armor": EDGY_ARMOR,
    "ultra_edgy_sword": ULTRA_EDGY_SWORD,
    "ultra_edgy_armor": ULTRA_EDGY_ARMOR,
    "omega_sword": OMEGA_SWORD,
    "omega_armor": OMEGA_ARMOR,
    "ultra_omega_sword": ULTRA_OMEGA_SWORD,
    "ultra_omega_armor": ULTRA_OMEGA_ARMOR,  # life_potion=1
    "godly_sword": GODLY_SWORD,  # dragon_essence=10
}

food_recipe_map = {
    "baked_fish": BAKED_FISH,
    "mutant_creature": MUTANT_CREATURE,
    "fruit_salad": FRUIT_SALAD,
    "apple_juice": APPLE_JUICE,
    "super_cookie": SUPER_COOKIE,
    "banana_pickaxe": BANANA_PICKAXE,
    "heavy_apple": HEAVY_APPLE,
    "filled_lootbox": FILLED_LOOTBOX,
    "coin_sandwich": COIN_SANDWICH,
    "fruit_ice_cream": FRUIT_ICE_CREAM,
}

gear_name_index = {idx: name for idx, name in enumerate(gear_recipe_map)}
food_name_index = {idx + len(gear_recipe_map): name for idx, name in enumerate(food_recipe_map)}

full_index = {
    **food_name_index,
    **gear_name_index,
    "food": food_name_index,
    "gear": gear_name_index,
}

full_map = {
    **food_recipe_map,
    **gear_recipe_map,
    "food": food_recipe_map,
    "gear": gear_recipe_map,
}

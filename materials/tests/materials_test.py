from unittest import TestCase

import crafting
from crafting.recipes import RUBY_SWORD, EDGY_ARMOR, EDGY_SWORD, FRUIT_SALAD


class TestFuture(TestCase):
    def test_future_runs(self):
        crafting.Inventory(
            2,
            wooden_log=100,
            epic_log=10,
            super_log=5,
            mega_log=5,
            normie_fish=30,
            golden_fish=17,
            epic_fish=1,
            apple=60000,
            banana=15,
        ).future()

    def test_future_is_accurate(self):
        inventory = crafting.Inventory(2, wooden_log=100_000)
        logs_in_area_10 = inventory.future()
        self.assertEqual(logs_in_area_10, 1_687_500, inventory.to_dict())

    def test_bad_call_raises(self):
        with self.assertRaises(AssertionError):
            crafting.Inventory(16, wooden_log=100_000)  # no trade table for area 16


class TestCanCraft(TestCase):
    real_inv = crafting.Inventory(
        **{
            item: int(qty)
            for item, qty in {
                "apple": "171799",
                "banana": "54",
                "golden_fish": "17",
                "wooden_log": "167",
                "epic_log": "24",
                "super_log": "15",
                "wolf_skin": "61",
                "zombie_eye": "56",
                "unicorn_horn": "60",
                "mermaid_hair": "28",
                "dragon_scale": "3",
                "common": "16",
                "uncommon": "5",
                "rare": "53",
                "epic": "3",
                "edgy": "4",
                "cookie": "14657",
            }.items()
        }
    )

    def test_ruby_sword(self):
        inventory = crafting.Inventory(wooden_log=400, super_log=1000)
        self.assertTrue(crafting.can_craft(RUBY_SWORD, inventory))
        inventory = crafting.Inventory(hyper_log=1)
        self.assertTrue(crafting.can_craft(RUBY_SWORD, inventory))
        inventory = crafting.Inventory(wooden_log=1000, super_log=1)
        self.assertFalse(crafting.can_craft(RUBY_SWORD, inventory))
        inventory = crafting.Inventory(wooden_log=1000, mermaid_hair=5)
        self.assertFalse(crafting.can_craft(RUBY_SWORD, inventory))

    def test_edgy_armor(self):
        inventory = crafting.Inventory(wolf_skin=65, zombie_eye=52, unicorn_horn=53, mermaid_hair=37, chip=15)
        self.assertTrue(crafting.can_craft(EDGY_ARMOR, inventory))
        inventory = crafting.Inventory(wolf_skin=65, zombie_eye=52, unicorn_horn=53, mermaid_hair=27)
        self.assertFalse(crafting.can_craft(EDGY_ARMOR, inventory))

    def test_real(self):
        self.assertTrue(crafting.can_craft(RUBY_SWORD, self.real_inv))
        # self.assertTrue(crafting.can_craft(EDGY_SWORD, self.real_inv))


class TestHowMany(TestCase):
    def test_how_many_fruit_salad(self):
        expected = 869
        inv = crafting.Inventory(area=10, apple=100_000)
        how_many, total_recipe = crafting.how_many(FRUIT_SALAD, inv)
        self.assertEqual(how_many, expected)
        self.assertEqual((FRUIT_SALAD * expected).inventory, total_recipe)

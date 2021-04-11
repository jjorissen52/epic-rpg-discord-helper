from unittest import TestCase

import crafting


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
    def test_ruby_sword(self):
        recipe = crafting.Inventory(wooden_log=400, mega_log=1, ruby=5)
        inventory = crafting.Inventory(wooden_log=400, super_log=1000)
        self.assertTrue(crafting.can_craft(recipe, inventory))
        inventory = crafting.Inventory(hyper_log=1)
        self.assertTrue(crafting.can_craft(recipe, inventory))

        inventory = crafting.Inventory(wooden_log=1000, super_log=1)
        self.assertFalse(crafting.can_craft(recipe, inventory))

    def test_edgy_armor(self):
        recipe = crafting.Inventory(wolf_skin=50, zombie_eye=50, unicorn_horn=50, mermaid_hair=35, chip=15)
        inventory = crafting.Inventory(wolf_skin=65, zombie_eye=52, unicorn_horn=53, mermaid_hair=37, chip=15)
        self.assertTrue(crafting.can_craft(recipe, inventory))
        inventory = crafting.Inventory(wolf_skin=65, zombie_eye=52, unicorn_horn=53, mermaid_hair=27)
        self.assertFalse(crafting.can_craft(recipe, inventory))

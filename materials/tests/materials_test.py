from unittest import TestCase

import materials


class TestFuture(TestCase):
    def test_future_runs(self):
        materials.future(2, 100, 10, 5, 5, 0, 0, 30, 17, 1, 60000, 15, 3)

    def test_future_is_accurate(self):
        logs_in_area_10 = materials.future(2, 100_000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert logs_in_area_10 == 1_687_500

    def test_bad_call_raises(self):
        with self.assertRaises(ValueError):
            materials.future(16, 100_000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)  # no trade table for area 16


class TestCanCraft(TestCase):
    def test_ruby_sword(self):
        recipe = [400, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 11]
        recipe.extend([0] * (materials.INVENTORY_SIZE - len(recipe)))
        inventory = [400, 0, 1000, 0, 0]
        inventory.extend([0] * (materials.INVENTORY_SIZE - len(inventory)))
        materials.can_craft(recipe, inventory)

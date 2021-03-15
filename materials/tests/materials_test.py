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
            materials.future(15, 100_000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)  # no trade table for area 15

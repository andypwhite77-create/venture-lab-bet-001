import unittest
from colony.spartan_alumni import bound_hold_minutes, HOLD_PROBE_HORIZONS

class SpartanAlumniHoldTests(unittest.TestCase):
    def test_arbitrary_holds_are_preserved_inside_range(self):
        self.assertEqual(4, bound_hold_minutes(4))
        self.assertEqual(6, bound_hold_minutes(6))
        self.assertEqual(17, bound_hold_minutes(17))

    def test_holds_are_bounded_not_snapped(self):
        self.assertEqual(3, bound_hold_minutes(1))
        self.assertEqual(240, bound_hold_minutes(999))

    def test_probe_set_spans_short_and_long(self):
        self.assertTrue(any(h < 5 for h in HOLD_PROBE_HORIZONS))
        self.assertTrue(any(h > 5 for h in HOLD_PROBE_HORIZONS))

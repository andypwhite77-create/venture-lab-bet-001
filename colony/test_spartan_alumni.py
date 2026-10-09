import unittest
from colony.spartan_alumni import bound_hold_minutes, HOLD_PROBE_HORIZONS, spartan_evidence_leaders

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

    def test_independent_spartan_maxima_have_distinct_genome_ids(self):
        x=spartan_evidence_leaders({
            'evidence_leader':{'n':60,'avg_return_pct':-.95,'median_return_pct':-2.6,'worst_return_pct':-37.8},
            'average_leader':{'n':12,'avg_return_pct':11.67,'median_return_pct':.36,'worst_return_pct':-23.7},
            'other':{'n':30,'avg_return_pct':0,'median_return_pct':-.2,'worst_return_pct':-10},
        })
        self.assertEqual(x['most_observations']['genome_id'],'evidence_leader')
        self.assertEqual(x['most_observations']['n'],60)
        self.assertEqual(x['highest_average']['genome_id'],'average_leader')
        self.assertEqual(x['highest_average']['n'],12)
        self.assertEqual(x['highest_average']['avg_return_pct'],11.67)
        self.assertEqual(spartan_evidence_leaders({}),{'most_observations':None,'highest_average':None})

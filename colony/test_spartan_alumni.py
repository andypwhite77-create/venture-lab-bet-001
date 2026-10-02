import unittest
from colony.spartan_alumni import SUPPORTED_OUTCOME_HORIZONS, supported_hold, normalize_evidence_horizon

class SpartanAlumniHorizonTests(unittest.TestCase):
    def test_supported_values_remain_unchanged(self):
        for h in SUPPORTED_OUTCOME_HORIZONS:
            self.assertEqual(h, supported_hold(h, 5))

    def test_unsupported_hold_preserves_mutation_away_from_parent(self):
        self.assertEqual(3, supported_hold(4, 5))
        self.assertEqual(8, supported_hold(6, 5))

    def test_seed_without_parent_uses_nearest_supported_horizon(self):
        self.assertEqual(5, supported_hold(4))
        self.assertEqual(5, supported_hold(6))

    def test_normalize_updates_genome_parameters(self):
        parent={'parameters':{'hold_minutes':5}}
        child={'parameters':{'hold_minutes':6,'threshold':1.0}}
        out=normalize_evidence_horizon(child,parent)
        self.assertEqual(8,out['parameters']['hold_minutes'])
        self.assertEqual(1.0,out['parameters']['threshold'])

if __name__=='__main__': unittest.main()

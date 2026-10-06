import inspect,unittest
import colony.continuous_evolution as ce

class ContinuousReliabilityPolicyTests(unittest.TestCase):
    def test_reversal_defaults_drive_faster_bounded_evolution(self):
        sig=inspect.signature(ce.evolve_reversal_forward)
        self.assertEqual(sig.parameters['births_per_cycle'].default,5)
        src=inspect.getsource(ce.evolve_reversal_forward)
        self.assertIn("birth_age_minutes<10",src)
        self.assertIn("parent_class=='reliable'",src)
        self.assertIn("'tail_repair_explore'",src)
        self.assertIn("r.get('win_rate',0)<.45",src)
        self.assertIn("bounded_research_turnover",src)
        self.assertIn("birth_age_minutes>=10",src)
        self.assertIn("reserve_repair_explore",src)
        self.assertIn("reserve_repair",src)
        self.assertIn("protected_elites",src)

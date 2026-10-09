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
        self.assertIn("clearly_failing_reversal_research_ant(r)",src)
        self.assertIn("bounded_research_turnover",src)
        self.assertIn("birth_age_minutes>=10",src)
        self.assertIn("reserve_repair_explore",src)
        self.assertIn("reserve_repair",src)
        self.assertIn("protected_elites",src)
        self.assertIn("parent_diagnostics",src)
        self.assertIn("breeding_wait_reason",src)

    def test_early_research_turnover_requires_clear_20_event_failure(self):
        f=ce.clearly_failing_reversal_research_ant
        self.assertFalse(f({'n':19,'win_rate':.10,'median_return_pct':-5,'avg_return_pct':-5}))
        self.assertTrue(f({'n':21,'win_rate':.38,'median_return_pct':-1.8,'avg_return_pct':.46}))
        self.assertFalse(f({'n':21,'win_rate':.40,'median_return_pct':-1.8,'avg_return_pct':-.2}))
        self.assertFalse(f({'n':21,'win_rate':.38,'median_return_pct':.5,'avg_return_pct':-2}))
        self.assertFalse(f({'n':23,'win_rate':.52,'median_return_pct':.23,'avg_return_pct':2.6}))
        self.assertTrue(f({'n':25,'win_rate':.44,'median_return_pct':.4,'avg_return_pct':1}))
        self.assertFalse(f({'n':25,'win_rate':.57,'median_return_pct':.8,'avg_return_pct':2}))

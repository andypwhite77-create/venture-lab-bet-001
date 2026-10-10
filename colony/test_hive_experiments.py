import unittest
from colony.hive_experiments import diagnosis
class ExperimentTests(unittest.TestCase):
 def test_insufficient_sample(self):self.assertIsNone(diagnosis(2,1,-0.02,-0.01))
 def test_positive_net_no_failure_trigger(self):self.assertIsNone(diagnosis(24,15,0.002,-0.001))
 def test_failure_is_falsifiable_and_cost_adjusted(self):
  x=diagnosis(24,14,-0.0123,-0.004)
  self.assertEqual(x['minimum_forward_trades'],30)
  self.assertFalse(x['baseline']['includes_rent'])
  self.assertIn('independent later sample',x['prediction'])

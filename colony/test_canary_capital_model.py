import unittest
from colony.canary_capital_model import replay
class ModelTest(unittest.TestCase):
 def test_no_negative_cash_or_refill(self):
  x=replay([-200,100]);self.assertEqual(x['end_gbp'],0);self.assertEqual(x['trades'],1)
 def test_cost_and_compounding(self):
  x=replay([2,2],extra_cost_pct=1);self.assertGreater(x['end_gbp'],25)

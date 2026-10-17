import unittest
from colony.queen_profit_pressure import assess
class PressureTests(unittest.TestCase):
 def test_blank_prospective_cohort_does_not_claim_profit(self):
  x=assess([])
  for value in x['policies'].values():
   self.assertEqual(value['net_mark_pnl_gbp'],0)
   self.assertEqual(value['free_cash_gbp'],125)
   self.assertEqual(value['survival_status'],'unproven_positive')
  self.assertIn('no higher leverage',x['no_shortcut'])

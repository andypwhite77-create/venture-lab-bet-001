import unittest
from colony.hive_forward_scoreboard import assess
class NegativeEconomicEvidence(unittest.TestCase):
 def test_less_negative_than_control_still_fails(self):
  rows=[{'challenger_net_pct':-2.5,'control_net_pct':-3.3} for _ in range(30)]
  self.assertEqual(assess(rows)['status'],'failed_paper')
 def test_positive_edge_with_better_tail_remains_paper_only(self):
  rows=[{'challenger_net_pct':0.5,'control_net_pct':0.2} for _ in range(30)]
  self.assertEqual(assess(rows)['status'],'supported_paper')

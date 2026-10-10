import unittest
from colony.hive_forward_scoreboard import assess
class ForwardScoreTests(unittest.TestCase):
 def test_no_paper_proof_without_pairs(self):self.assertEqual(assess([])['status'],'insufficient_evidence')
 def test_supported_only_with_positive_uplift_and_better_tail(self):
  rows=[{'challenger_net_pct':2,'control_net_pct':1} for _ in range(30)]
  self.assertEqual(assess(rows)['status'],'supported_paper')
 def test_negative_uplift_is_failure(self):
  rows=[{'challenger_net_pct':-2,'control_net_pct':1} for _ in range(30)]
  self.assertEqual(assess(rows)['status'],'failed_paper')

import unittest
from colony.hive_matched_path_research import matched_edges
class MatchedEdgesTests(unittest.TestCase):
 def test_missing_control_is_not_matched(self):
  rows=[{'candidate_id':1,'species':'observation_control','status':'observed_path','net_pct':1.0},
  {'candidate_id':1,'species':'oversold','status':'observed_path','net_pct':2.0},
  {'candidate_id':2,'species':'oversold','status':'observed_path','net_pct':10.0}]
  res=matched_edges(rows)['oversold'];self.assertEqual(res['matched_distinct_opportunities'],1);self.assertEqual(res['mean_paper_edge_pct_points'],1)

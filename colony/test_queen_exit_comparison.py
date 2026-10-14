import unittest
from colony.queen_exit_comparison import compare, POLICIES
class ComparisonTests(unittest.TestCase):
 def test_missing_control_not_counted(self):
  x={'candidate_id':3,'control':{'status':'insufficient_path'}}
  x.update({p:{'status':'observed_path','net_pct':3.0} for p in POLICIES})
  r=compare([x]);self.assertEqual(r['policies']['stop_10']['distinct_paired_opportunities'],0)
 def test_matched_delta(self):
  x={'candidate_id':4,'control':{'status':'observed_path','net_pct':-30.0}}
  x.update({p:{'status':'observed_path','net_pct':-10.0} for p in POLICIES})
  r=compare([x]);self.assertEqual(r['policies']['stop_10']['mean_edge_pct_points'],20.0)

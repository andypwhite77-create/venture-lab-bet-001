import unittest
from colony.exit_paired_summary import summarize
class PairedTests(unittest.TestCase):
 def test_pairs_only_complete_cases(self):
  good={'control':{'status':'observed_path','net_pct':-20},'take_10':{'status':'observed_path','net_pct':-10},'stop_10_take_15':{'status':'observed_path','net_pct':-5}}
  bad={'control':{'status':'observed_path','net_pct':200}}
  r=summarize([{'outcome':good},{'outcome':bad}])
  self.assertEqual(r['paired_candidates'],1)
  self.assertEqual(r['excluded'],1)
  self.assertEqual(r['policies']['stop_10_take_15']['mean_paired_delta_pp'],15)
 def test_empty_not_profitable(self):
  r=summarize([])
  self.assertIsNone(r['policies']['control']['mean_sampled_net_pct'])

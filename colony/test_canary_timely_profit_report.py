import unittest
from colony.canary_timely_profit_report import summarize
class TimelyTest(unittest.TestCase):
 def test_shared_candidates_not_independent(self):
  def row(n):
   return {'candidate_id':7,'entry_id':n,'mint':'X','genome_id':str(n),'entry_quote':{'in_amount':'10000000','out_amount':'100'},'exit_quote':{'in_amount':'100','out_amount':'11000000'},'entry_latency':.1,'exit_latency':.2,'entry_source':'birth','exit_source':'precise_exit'}
  x=summarize([row(1),row(2)]);self.assertEqual(x['timely_distinct_candidates'],1);self.assertFalse(x['research_gate_met'])

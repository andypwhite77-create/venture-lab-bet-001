import unittest
from colony.plasticity_execution_review import classify,assess
class EvidenceTests(unittest.TestCase):
 def test_fast_requires_both(self):
  r={'entry_status':'quoted','exit_status':'quoted','entry_latency':.1,'exit_latency':30}
  self.assertEqual(classify(r),'delayed_pair')
  r['exit_latency']=.2;self.assertEqual(classify(r),'timely_pair_not_fill')
 def test_abstention_counts_counterfactual(self):
  r={'entry_id':1,'genome_id':'a','candidate_id':42,'action':'abstain','paper_pnl_gbp':5,
    'entry_status':None,'exit_status':None,'entry_latency':None,'exit_latency':None}
  x=assess([r]);self.assertEqual(x['plasticity_abstention_by_genome']['a']['missed_winners'],1)

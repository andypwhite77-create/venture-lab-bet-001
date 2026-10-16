import unittest
from colony.unresolved_outcome_reconciliation import explain
class ReconcileTests(unittest.TestCase):
 def test_quote_without_outcome_not_promoted_to_close(self):
  r={'entry_id':1,'candidate_id':2,'matching_horizon_outcomes':0,'eligible_outcomes':0,'entry_quote':None,'exit_quote':{'out_amount':'100'},'entry_latency':None,'exit_latency':.1}
  o=explain([r])['positions'][0]
  self.assertEqual(o['reason'],'no_matching_horizon_research_outcome')
  self.assertFalse(o['paired_quote_only'])
 def test_backlog_identified(self):
  r={'entry_id':3,'candidate_id':4,'matching_horizon_outcomes':2,'eligible_outcomes':1,'entry_quote':None,'exit_quote':None,'entry_latency':None,'exit_latency':None}
  self.assertEqual(explain([r])['positions'][0]['reason'],'eligible_outcome_exists_ledger_not_ingested')

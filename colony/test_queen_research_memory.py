import unittest
from colony.queen_historical_autoresearch import allowed
from colony.queen_research_memory import summarize
from colony.queen_research_incentives import grade
class MemoryTests(unittest.TestCase):
 def test_duplicate_rejected(self):
  memory={'experiments':[{'feature':'volume_m5','direction':'low'}]}
  self.assertFalse(allowed('volume_m5','low',memory))
  self.assertTrue(allowed('volume_m5','high',memory))
  self.assertFalse(allowed('secret','high',memory))
 def test_refuted_hypothesis_has_no_credit(self):
  result={'status':'historical_discovery_only','training':{'selected_mean_pct':1,'other_mean_pct':0},'chronological_mint_holdout':{'selected_mean_pct':-1,'other_mean_pct':0,'selected_n':20,'other_n':20}}
  report=summarize([{'queen':'reversal','feature':'volume_m5','direction':'low','result':result}])
  self.assertEqual(report['queens']['reversal']['historical_flags'],0)
  self.assertEqual(grade(result)['status'],'historically_refuted')

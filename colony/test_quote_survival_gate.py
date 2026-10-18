import unittest
from colony.quote_survival_gate import verdict
class GateTests(unittest.TestCase):
 def test_missing_is_not_eligible(self):self.assertFalse(verdict('x',{})['eligible'])
 def test_profitable_but_unresolved_is_rejected(self):
  self.assertFalse(verdict('x',{'x':{'quote_pairs':30,'stressed_net_sol':1,'missing_or_invalid_pairs':1}})['eligible'])
 def test_qualified_research_only(self):
  b={'quote_pairs':26,'stressed_net_sol':.01,'missing_or_invalid_pairs':0,'blocked_by_simulated_cash':0,'unresolved_reserved_sol':0,'capital_reconciled':True,'cash_event_rejections':0}
  self.assertTrue(verdict('x',{'x':b})['eligible'])

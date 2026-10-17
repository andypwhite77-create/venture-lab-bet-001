import unittest
from colony.survival_floor import decide
class SurvivalFloorTests(unittest.TestCase):
 def test_short_positive_run_is_rejected(self):
  v={'policies':{'plasticity':{'completed_marks':3,'net_mark_pnl_gbp':5,'book_equity_gbp':130,'overdue_positions':0}}}
  x=decide(v,1);self.assertFalse(x['policy_assessments']['plasticity']['research_floor_candidate'])
  self.assertFalse(x['floor_active'])
 def test_loss_cannot_pass_by_volume(self):
  v={'policies':{'fixed_dna':{'completed_marks':100,'net_mark_pnl_gbp':-1,'book_equity_gbp':124,'overdue_positions':0}}}
  self.assertFalse(decide(v,30)['policy_assessments']['fixed_dna']['research_floor_candidate'])
 def test_positive_provisional_still_not_auto_activated(self):
  v={'policies':{'plasticity':{'completed_marks':100,'net_mark_pnl_gbp':5,'book_equity_gbp':130,'overdue_positions':0}}}
  x=decide(v,8);self.assertTrue(x['policy_assessments']['plasticity']['research_floor_candidate']);self.assertFalse(x['floor_active'])

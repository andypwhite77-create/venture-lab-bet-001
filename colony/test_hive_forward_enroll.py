import unittest
from colony.hive_forward_enroll import cohort
from colony.genome import genome_id
class CohortTests(unittest.TestCase):
 def test_frozen_matching_entries_and_distinct_challengers(self):
  base={'family':'queen_pattern','species':'general_pattern','parameters':{'hold_minutes':60,'stop_loss_pct':None,'take_profit_pct':None},'predicates':{'price_change_m5':{'max':3}},'bounds':{}}
  agents=cohort(base,8)
  self.assertEqual(len(agents),9)
  self.assertEqual(sum(is_control for _,is_control in agents),1)
  self.assertEqual(len({genome_id(g) for g,_ in agents}),9)
  self.assertTrue(all(g['predicates']==base['predicates'] for g,_ in agents))
  self.assertEqual(base['parameters']['hold_minutes'],60)

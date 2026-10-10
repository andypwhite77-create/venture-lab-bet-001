import random,unittest
from colony.queen_pattern_recognition import targeted_loss_challenger
class TargetedLossChallengerTests(unittest.TestCase):
 def test_bounded_exits_and_parent_is_unchanged(self):
  parent={'family':'queen_pattern','predicates':{'price_change_m5':{'max':2}},'parameters':{'hold_minutes':60,'stop_loss_pct':None,'take_profit_pct':None}}
  child=targeted_loss_challenger(parent,random.Random(7))
  self.assertEqual(child['predicates'],parent['predicates'])
  self.assertEqual(parent['parameters']['hold_minutes'],60)
  self.assertIn(child['parameters']['stop_loss_pct'],(-5,-8,-12))
  self.assertIn(child['parameters']['take_profit_pct'],(5,8,12,20))
  self.assertIn(child['parameters']['hold_minutes'],(5,10,15,30))

import unittest
from datetime import datetime,timezone
from colony.queen_feedback_refresh import snapshot
class Tests(unittest.TestCase):
 def test_no_awarded_capacity(self):
  x=snapshot({'families':{},'unmapped_count':0},datetime(2026,10,18,tzinfo=timezone.utc))
  self.assertFalse(x['reward_authorized'])
  self.assertEqual(x['research_capacity_increase'],0)
  self.assertEqual(x['feedback']['authority'],'diagnostic_only_no_budget_increase')

import unittest
from colony.queen_economic_feedback import explain
class Tests(unittest.TestCase):
 def test_losses_are_priorities_not_rewards(self):
  x=explain({'families':{'exhaustion':[{'completed_quote_round_trips':9,'pending_positions':1,'realized_hypothetical_net_sol':-.02,'locked_sol':.01,'realized_drawdown_sol':.02}]},'unmapped_count':0})['families']['exhaustion']
  self.assertIn('investigate_negative_quote_economics',x['research_priorities'])
  self.assertIn('investigate_unresolved_capital',x['research_priorities'])
  self.assertEqual(x['budget_bonus'],0)
  self.assertIsNone(x['economic_reward'])

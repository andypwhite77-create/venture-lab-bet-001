import unittest
from colony.queen_research_objectives import objective_prompt
class Tests(unittest.TestCase):
 def test_economic_losses_are_not_claimed_as_causes(self):
  p=objective_prompt({'feedback':{'research_priorities':['investigate_loss_tail'],'hypothetical_net_sol':-.02,'pending':0}})
  self.assertIn('investigate_loss_tail',p)
  self.assertIn('NOT proven causes',p)
 def test_missing_fails_safe(self):
  self.assertIn('No attributed',objective_prompt({'feedback':None}))

import unittest
from colony.queen_treasury import evaluate
class TreasuryTests(unittest.TestCase):
 def test_cost_not_hidden(self):
  report=evaluate([{'status':'closed','net_pnl_usd':1},{'status':'open','net_pnl_usd':None}],[],[{'queen':'eth','cost_usd':2}])
  self.assertEqual(report['eth']['hypothetical_marks_less_logged_cost_usd'],-1)
  self.assertEqual(report['eth']['capital_reserved_usd'],25)
  self.assertIn('Incomplete',report['cost_coverage'])
 def test_shared_solana_allocations_not_double_counted(self):
  report=evaluate([], [{'attributed_net_sol':0.1},{'attributed_net_sol':-0.2}],[])
  self.assertAlmostEqual(report['solana']['executor_recorded_attributed_pnl_sol'],-0.1)

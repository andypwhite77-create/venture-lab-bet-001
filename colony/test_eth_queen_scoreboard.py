import unittest
from colony.eth_queen_scoreboard import assess
class TestEthScoreboard(unittest.TestCase):
 def test_open_capital_is_not_profit(self):
  a=assess([{'strategy':'momentum','status':'open','net_pnl_usd':None}])['arms']['momentum']
  self.assertEqual(a['available_cash_usd'],100)
  self.assertEqual(a['closed_net_usd'],0)
 def test_loss_survives(self):
  a=assess([{'strategy':'reversal','status':'closed','net_pnl_usd':-3}])['arms']['reversal']
  self.assertEqual(a['book_equity_usd'],122)
  self.assertEqual(a['research_status'],'insufficient_evidence')

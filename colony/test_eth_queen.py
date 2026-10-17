import unittest
from colony.eth_queen import signal,net_pnl
class EthQueenTests(unittest.TestCase):
 def test_momentum(self):
  candles=[[1,0,0,0,'90'],[2,0,0,0,'95'],[3,0,0,0,'100'],[4,0,0,0,'110']]
  self.assertTrue(signal('momentum',candles))
  self.assertFalse(signal('reversal',candles))
 def test_costs_deducted(self):
  self.assertAlmostEqual(net_pnl(100,100),-0.1)
 def test_gain_after_cost(self):
  self.assertAlmostEqual(net_pnl(100,102),0.4)

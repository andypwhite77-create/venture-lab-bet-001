import unittest
from colony.major_market_paper import closed_candles,momentum_signal,PAIRS
class PaperMarketTests(unittest.TestCase):
 def test_current_unclosed_candle_excluded(self):
  row=lambda t,p:[t,p,p,p,p,p,1,2]
  raw={'error':[],'result':{'XETHZUSD':[row(100,'10'),row(200,'15')],'last':200}}
  x=closed_candles(raw,'ETHUSD')
  self.assertEqual(len(x),1)
  self.assertEqual(x[0]['ts'],100)
 def test_insufficient_history_never_opens(self):
  self.assertFalse(momentum_signal([1.0]*24))
 def test_no_executable_venue_in_registry(self):
  self.assertEqual(set(PAIRS),{'ethereum_scout','solana_major_scout'})

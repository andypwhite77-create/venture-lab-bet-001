import unittest
from colony.eth_opportunity_scout import hypotheses
class ScoutTests(unittest.TestCase):
 def test_continuation(self):
  candles=[[i,0,110,90,str(100+i)] for i in range(13)]
  self.assertIn('continuation',hypotheses(candles))
 def test_flat_abstains(self):
  candles=[[i,0,110,90,'100'] for i in range(13)]
  self.assertEqual(hypotheses(candles),[])

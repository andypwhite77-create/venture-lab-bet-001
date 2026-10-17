import unittest
from colony.eth_evolution import seeds,signal_genome,child_of
class TestEthEvolution(unittest.TestCase):
 def test_seeds_unique(self):
  items=seeds();self.assertEqual(len(items),len(set(x[0] for x in items)))
 def test_no_future_bar(self):
  candles=[[i,0,0,0,str(p)] for i,p in enumerate([100,101,102,103])]
  self.assertTrue(signal_genome('momentum',2,0,candles))
  self.assertFalse(signal_genome('reversal',2,0,candles))
 def test_mutation_bounded(self):
  c=child_of(seeds()[0],1);self.assertGreaterEqual(c[2],2);self.assertLessEqual(c[3],.02)

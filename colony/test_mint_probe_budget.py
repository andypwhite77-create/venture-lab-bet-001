import unittest
from path_sampler import update_mint_misses,_MINT_MISS_STREAK,_MINT_BIRDEYE_PROBE_AFTER
class MintProbeBudgetTests(unittest.TestCase):
 def setUp(self):
  _MINT_MISS_STREAK.clear();_MINT_BIRDEYE_PROBE_AFTER.clear()
 def test_streak_and_recovery(self):
  for _ in range(5):update_mint_misses(['token'],{},now=100)
  self.assertEqual(_MINT_MISS_STREAK['token'],5)
  self.assertEqual(_MINT_BIRDEYE_PROBE_AFTER['token'],700)
  update_mint_misses(['token'],{'token':.02},now=120)
  self.assertNotIn('token',_MINT_MISS_STREAK)
  self.assertNotIn('token',_MINT_BIRDEYE_PROBE_AFTER)
 def test_disappeared_token_pruned(self):
  update_mint_misses(['token'],{},now=100)
  update_mint_misses([],{},now=101)
  self.assertNotIn('token',_MINT_MISS_STREAK)

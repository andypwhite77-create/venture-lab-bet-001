import unittest
from colony.capital_preservation_shadow import classify
from colony.queen_roles import BREEDING_QUEEN,SWARM_QUEEN
class EconomicResearchTests(unittest.TestCase):
 def test_high_liquidity_stable_passes(self):
  self.assertEqual(classify({'liquidity_usd':125000,'price_change_m5':-8,'price_change_h1':-10}),[])
 def test_liquidity_and_crash_flag(self):
  x=classify({'liquidity_usd':35000,'price_change_m5':-14,'price_change_h1':-27})
  self.assertEqual(len(x),3)
 def test_queens_not_traders(self):
  self.assertIn('trade_or_sign',BREEDING_QUEEN['forbidden'])
  self.assertIn('trade_or_sign',SWARM_QUEEN['forbidden'])

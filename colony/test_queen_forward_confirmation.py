import unittest
from colony.queen_forward_confirmation import classify
class Tests(unittest.TestCase):
 def test_both_conditions(self):
  f=['liquidity_usd','volume_m5'];d=['low','high'];t=[100,10]
  self.assertTrue(classify(f,d,t,{'liquidity_usd':80,'volume_m5':20}))
  self.assertFalse(classify(f,d,t,{'liquidity_usd':120,'volume_m5':20}))
  self.assertFalse(classify(f,d,t,{'liquidity_usd':80,'volume_m5':9}))
 def test_missing_is_not_negative(self):
  self.assertIsNone(classify(['liquidity_usd','volume_m5'],['low','high'],[100,10],{'volume_m5':20}))

import unittest
from colony.hive_governor import verdict
class GovernorTests(unittest.TestCase):
 def test_negative_below_limit_with_sample_disarms(self):self.assertEqual(verdict(24,-0.01234),'disarm_loss_limit')
 def test_sparse_data_does_not_disarm(self):self.assertEqual(verdict(2,-0.03),'observe')
 def test_breakeven_safe(self):self.assertEqual(verdict(24,0),'observe')

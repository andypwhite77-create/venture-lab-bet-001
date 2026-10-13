import unittest
from path_sampler import provider_allowed,provider_result,_PROVIDER_BLOCK_UNTIL
class ProviderBudgetTests(unittest.TestCase):
 def tearDown(self):_PROVIDER_BLOCK_UNTIL.clear()
 def test_rate_limit_opens_gate(self):
  provider_result('birdeye_price',{'ok':False,'error':'HTTP_429'},now=100)
  self.assertFalse(provider_allowed('birdeye_price',now=399))
  self.assertTrue(provider_allowed('birdeye_price',now=400))
 def test_other_source_not_blocked(self):
  provider_result('birdeye_price',{'ok':False,'error':'HTTP_429'},now=100)
  self.assertTrue(provider_allowed('coingecko_price',now=101))

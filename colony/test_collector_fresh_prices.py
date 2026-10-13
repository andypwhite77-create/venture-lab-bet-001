import unittest
from unittest.mock import AsyncMock,patch
import collector_fresh_prices as collector

class FreshCollectorTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  collector._BLOCKED_UNTIL=0
 async def test_requests_network_even_with_discovery_cache(self):
  item={'attributes':{'address':'A','price_usd':'3.25'}}
  with patch.object(collector.marketdata,'_get_json',new=AsyncMock(return_value={'data':[item]})) as request:
   prices,error=await collector.fetch(['A'])
  self.assertEqual(prices,{'A':3.25});self.assertIsNone(error)
  request.assert_awaited_once()
 async def test_rejects_invalid_and_unrequested_price(self):
  rows=[{'attributes':{'address':'A','price_usd':'0'}},{'attributes':{'address':'B','price_usd':'3'}},{'attributes':{'address':'C','price_usd':'NaN'}}]
  with patch.object(collector.marketdata,'_get_json',new=AsyncMock(return_value={'data':rows})):
   prices,error=await collector.fetch(['A','C'])
  self.assertEqual(prices,{})
 async def test_rate_limit_opens_circuit(self):
  with patch.object(collector.marketdata,'_get_json',new=AsyncMock(side_effect=Exception('HTTP 429'))) as request:
   prices,error=await collector.fetch(['A'])
   later,why=await collector.fetch(['A'])
  self.assertEqual(prices,{});self.assertEqual(later,{});self.assertEqual(why,'cooldown');request.assert_awaited_once()

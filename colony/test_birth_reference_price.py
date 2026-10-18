import unittest
from unittest.mock import patch
from colony import birth_reference_price as b
class BirthReferenceTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  b._WINDOW.clear();b._BLOCKED_UNTIL=0
 async def test_unavailable_stays_unpriced(self):
  async def empty(_):return {},None
  with patch.object(b,'dex_fetch',empty):
   self.assertIsNone(await b.capture('mint'))
 async def test_price_is_discovery_only(self):
  async def quote(_):return {'mint':0.01},None
  with patch.object(b,'dex_fetch',quote):
   result=await b.capture('mint')
  self.assertEqual(result['price_usd'],0.01)
  self.assertEqual(result['price_evidence'],'discovery_only_no_provider_tick_timestamp')
  self.assertIsNone(result['price_observed_at'])
 async def test_eight_request_budget(self):
  calls=[]
  async def empty(_):calls.append(True);return {},None
  with patch.object(b,'dex_fetch',empty):
   for _ in range(10):await b.capture('mint')
  self.assertEqual(len(calls),8)

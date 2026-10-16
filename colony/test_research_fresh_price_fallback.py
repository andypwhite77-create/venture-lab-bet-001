import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import AsyncMock,patch
from contextlib import asynccontextmanager
from research import _fresh_archived_entry_price
class FreshPriceTests(unittest.IsolatedAsyncioTestCase):
 async def test_fresh_same_mint_price_has_provenance(self):
  conn=AsyncMock();conn.fetchrow.return_value={'price':2.5,'provider':'geckoterminal','collected_at':datetime.now(timezone.utc),'source_observed_at':None}
  @asynccontextmanager
  async def fake():yield conn
  with patch('research.connection',fake):result=await _fresh_archived_entry_price('X')
  self.assertEqual(result['price_usd'],2.5)
  self.assertEqual(result['source'],'independent_fresh_history')
  self.assertEqual(conn.fetchrow.call_args.args[1],'X')
  self.assertIn("30 seconds",conn.fetchrow.call_args.args[0])
 async def test_missing_observation_does_not_invent_price(self):
  conn=AsyncMock();conn.fetchrow.return_value=None
  @asynccontextmanager
  async def fake():yield conn
  with patch('research.connection',fake):self.assertIsNone(await _fresh_archived_entry_price('X'))

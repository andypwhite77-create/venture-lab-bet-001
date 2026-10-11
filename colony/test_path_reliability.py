import unittest
from unittest.mock import AsyncMock,patch
import path_sampler
class SamplerReliabilityTests(unittest.IsolatedAsyncioTestCase):
 async def test_deduplicates_mints_but_writes_each_candidate(self):
  rows=[{'id':1,'mint':'X'},{'id':2,'mint':'X'},{'id':3,'mint':'Y'}]
  with patch.object(path_sampler,'active_shadow_candidates',new=AsyncMock(return_value=rows)),patch.object(path_sampler,'fetch_prices',new=AsyncMock(return_value={'X':1.0})) as fetch,patch.object(path_sampler,'record_price_path',new=AsyncMock()) as record:
   result=await path_sampler.sample_active_paths()
  fetch.assert_awaited_once_with(['X','Y'])
  self.assertEqual(record.await_count,2)
  self.assertEqual(result['missing'],1)
  self.assertEqual(result['missing_mints'],['Y'])

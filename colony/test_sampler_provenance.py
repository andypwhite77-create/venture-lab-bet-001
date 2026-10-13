import time,unittest
from unittest.mock import AsyncMock,patch
import path_sampler
class ProvenanceTests(unittest.IsolatedAsyncioTestCase):
 async def test_old_gecko_cache_cannot_be_written_as_fresh(self):
  rows=[{'id':1,'mint':'A'}]
  with patch.object(path_sampler,'active_shadow_candidates',new=AsyncMock(return_value=rows)),patch.object(path_sampler,'fetch_prices',new=AsyncMock(return_value={'A':5.0})),patch.dict(path_sampler.marketdata._GECKO_CACHE,{'A':(time.time()-100,{'price_usd':5.0})}),patch.object(path_sampler,'birdeye_price',new=AsyncMock(return_value={'ok':False})),patch.object(path_sampler,'coingecko_price',new=AsyncMock(return_value={'ok':False})),patch.object(path_sampler,'record_price_path',new=AsyncMock()) as record:
   result=await path_sampler.sample_active_paths()
  record.assert_not_awaited();self.assertEqual(result['missing'],1)
 async def test_fresh_gecko_has_lineage(self):
  rows=[{'id':1,'mint':'A'}]
  with patch.object(path_sampler,'active_shadow_candidates',new=AsyncMock(return_value=rows)),patch.object(path_sampler,'fetch_prices',new=AsyncMock(return_value={'A':5.0})),patch.dict(path_sampler.marketdata._GECKO_CACHE,{'A':(time.time(),{'price_usd':5.0})}),patch.object(path_sampler,'record_price_path',new=AsyncMock()) as record:
   await path_sampler.sample_active_paths()
  record.assert_awaited_once_with(1,5.0,'geckoterminal','fresh_fetch')

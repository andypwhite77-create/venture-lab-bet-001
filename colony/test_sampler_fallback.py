import unittest
from unittest.mock import AsyncMock,patch
import path_sampler
class FallbackTests(unittest.IsolatedAsyncioTestCase):
 async def test_missing_mint_uses_independent_provider(self):
  rows=[{'id':7,'mint':'A'}]
  with patch.object(path_sampler,'active_shadow_candidates',new=AsyncMock(return_value=rows)),patch.object(path_sampler,'fetch_fresh_prices',new=AsyncMock(return_value=({},None))),patch.object(path_sampler,'birdeye_price',new=AsyncMock(return_value={'ok':True,'provider':'birdeye','price_usd':2.5})),patch.object(path_sampler,'coingecko_price',new=AsyncMock()) as cg,patch.object(path_sampler,'record_price_path',new=AsyncMock()) as rec:
   result=await path_sampler.sample_active_paths()
  rec.assert_awaited_once_with(7,2.5,'birdeye','fresh_fetch');cg.assert_not_awaited();self.assertEqual(result['fallback_mints'],{'A':'birdeye'})
 async def test_failed_providers_cannot_fake_price(self):
  with patch.object(path_sampler,'active_shadow_candidates',new=AsyncMock(return_value=[{'id':7,'mint':'A'}])),patch.object(path_sampler,'fetch_fresh_prices',new=AsyncMock(return_value=({},None))),patch.object(path_sampler,'birdeye_price',new=AsyncMock(return_value={'ok':False})),patch.object(path_sampler,'coingecko_price',new=AsyncMock(return_value={'ok':False})),patch.object(path_sampler,'record_price_path',new=AsyncMock()) as rec:
   result=await path_sampler.sample_active_paths()
  rec.assert_not_awaited();self.assertEqual(result['recorded'],0)

import unittest
from colony.replay import flatten

class ReplayMissingnessTests(unittest.TestCase):
    def test_legacy_token_multi_pool_placeholders_are_unknown(self):
        row={'mint':'x','features':{'buys_15':3,'sells_15':1,'buys_30':4,'sells_30':2,'prev_buys_15':1},
             'market':{'source':'geckoterminal_token_multi','pair_address':None,'price_change_m5':0.0,
                       'price_change_h1':0.0,'volume_m5':0.0,'volume_h1':0.0,'buys_m5':0,'sells_m5':0,
                       'buys_h1':0,'sells_h1':0,'liquidity_usd':50000}}
        f=flatten(row)
        self.assertNotIn('price_change_m5',f)
        self.assertNotIn('volume_liquidity_m5',f)
        self.assertNotIn('dex_buy_ratio_m5',f)
        self.assertAlmostEqual(f['flow_imbalance_15'],0.5)
        self.assertEqual(f['buy_activity_change'],2.0)

    def test_explicit_features_override_partial_market(self):
        row={'mint':'x','features':{'price_change_m5':4.0,'price_change_h1':8.0,'volume_m5':1000.0},
             'market':{'source':'geckoterminal_token_multi','pair_address':None,'price_change_m5':0.0,
                       'price_change_h1':0.0,'volume_m5':0.0,'liquidity_usd':50000}}
        f=flatten(row)
        self.assertEqual(f['price_change_m5'],4.0)
        self.assertEqual(f['price_change_h1'],8.0)
        self.assertAlmostEqual(f['volume_liquidity_m5'],0.02)

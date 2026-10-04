import unittest
from colony.recovery_assessment import _derive, _pct, _quote_out

class RecoveryAssessmentTests(unittest.TestCase):
    def test_pct_uses_trade_basis(self):
        self.assertAlmostEqual(_pct(-0.0015614939421602792,0.010888501742160278),-14.3407,places=3)

    def test_quote_out_prefers_minimum(self):
        self.assertEqual(_quote_out({'amountOut':'0.011','minAmountOut':'0.0108'}),0.0108)

    def test_derive_measures_recovery_and_market_deterioration(self):
        e=_derive({
          'entry_market':{'price_usd':1.0,'liquidity_usd':100000},
          'latest_market':{'price_usd':0.8,'liquidity_usd':40000,'price_change_h1':-55,'dex_buy_ratio_m5':0.3},
          'strategy_exit_min_sol':0.0093,'recovery_best_min_sol':0.0102,'recovery_last_min_sol':0.0101,
          'recovery_last_reason':'recovery_quote_price_impact'})
        self.assertAlmostEqual(e['price_change_since_entry_pct'],-20.0)
        self.assertAlmostEqual(e['liquidity_change_since_entry_pct'],-60.0)
        self.assertGreater(e['recovery_improvement_vs_horizon_pct'],9.0)
        self.assertIn('liquidity_down_50pct',e['danger_flags'])
        self.assertIn('h1_down_50pct',e['danger_flags'])
        self.assertIn('buyers_below_35pct_m5',e['danger_flags'])
        self.assertIn('exit_price_impact_rejected',e['danger_flags'])

if __name__=='__main__': unittest.main()

class RecoveryAssessmentParserTests(unittest.TestCase):
    def test_parser_accepts_fenced_json(self):
        from colony.recovery_assessment import _parse_model_json
        x=_parse_model_json('```json\n{"classification":"UNCERTAIN"}\n```')
        self.assertEqual(x['classification'],'UNCERTAIN')

    def test_model_snapshot_excludes_full_path(self):
        from colony.recovery_assessment import _model_snapshot
        x=_model_snapshot({'assessment_kind':'current','market_path':[1,2,3],
          'current_quote':{'pnl_pct':-20},'danger_flags':['x']})
        self.assertNotIn('market_path',x)
        self.assertEqual(x['current_quote']['pnl_pct'],-20)

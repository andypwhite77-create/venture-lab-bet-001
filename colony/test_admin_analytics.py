import unittest
from datetime import datetime, timezone
from colony.admin_analytics import build_trade_metrics, paper_gate_status, estimated_position

NOW=datetime(2026,10,9,5,0,tzinfo=timezone.utc)

def trade(i,pnl,basis=.01,wallet=.03,fees=.00002):
    return {
        "id":i,"candidate_id":1000+i,"mint":f"mint{i}","status":"closed","broadcast":True,
        "created_at":NOW,"updated_at":NOW,"requested_gbp":1.0,"requested_sol":basis,
        "wallet_sol":wallet,"hold_minutes":5,"votes":5,"active_ants":5,
        "execution":{"mode":"live","closed_at":NOW.isoformat(),"entry_trade_sol":basis,
                     "realized_market_pnl_after_network_fees_sol":pnl,
                     "realized_network_fees_sol":fees}
    }

class AdminAnalyticsTests(unittest.TestCase):
    def test_realised_metrics_and_drawdown(self):
        m=build_trade_metrics([trade(1,.001),trade(2,-.0005),trade(3,.0002)],100.0,.0307)
        s=m["summary"]
        self.assertEqual(s["closed_trades"],3)
        self.assertEqual(s["wins"],2)
        self.assertEqual(s["losses"],1)
        self.assertAlmostEqual(s["realized_pnl_sol"],.0007)
        self.assertAlmostEqual(s["realized_pnl_gbp"],.07)
        self.assertAlmostEqual(s["profit_factor"],2.4)
        self.assertGreater(s["max_drawdown_sol"],0)
        self.assertEqual(len(m["series"]),3)

    def test_rejected_rows_do_not_count_as_trades(self):
        rejected=trade(4,.5)
        rejected["status"]="rejected"
        rejected["broadcast"]=False
        m=build_trade_metrics([rejected],100.0,.03)
        self.assertEqual(m["summary"]["closed_trades"],0)
        self.assertEqual(m["summary"]["realized_pnl_sol"],0)

    def test_paper_gate(self):
        good={"n":25,"days":3,"win_rate":.6,"median":.5,"worst":-10,"positive_day_rate":.7,"mean":2}
        self.assertTrue(paper_gate_status(good)["ready"])
        good["n"]=24
        x=paper_gate_status(good)
        self.assertFalse(x["ready"])
        self.assertEqual(x["gap_to_25"],1)

    def test_position_estimate_uses_safe_minimum(self):
        row={"id":1,"candidate_id":2,"mint":"m","status":"recovery","hold_minutes":5,"requested_sol":.01,
             "execution":{"entry_trade_sol":.01,"recovery_last_quote":{"minAmountOut":".009"}}}
        x=estimated_position(row)
        self.assertAlmostEqual(x["estimated_pnl_sol"],-.001)
        self.assertAlmostEqual(x["estimated_pnl_pct"],-10)

if __name__=="__main__":
    unittest.main()

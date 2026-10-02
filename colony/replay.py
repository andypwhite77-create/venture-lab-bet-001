"""Replay archived V1 observations through a whole ant population."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from colony.evaluator import matches
from colony.genome import genome_id

def flatten(row: dict) -> dict:
    # Raw market context is lower precedence than explicit research features.
    features = row.get("features") or {}
    market = row.get("market") or {}
    if isinstance(features, str):
        try: features=json.loads(features)
        except Exception: features={}
    if isinstance(market, str):
        try: market=json.loads(market)
        except Exception: market={}
    out = dict(market); out.update(features)
    out.update({k: row.get(k) for k in ("mint","created_at","entry_price")})

    # Legacy Gecko token/multi rows used literal zero placeholders for pool metrics
    # the endpoint did not actually observe. Convert those placeholders back to UNKNOWN.
    if market.get("source") == "geckoterminal_token_multi" and not market.get("pair_address"):
        unavailable=("volume_m5","volume_h1","price_change_m5","price_change_h1",
                     "buys_m5","sells_m5","buys_h1","sells_h1")
        for k in unavailable:
            if k not in features: out.pop(k,None)

    def observed(k):
        return k in out and out.get(k) is not None
    def f(k):
        try: return float(out.get(k))
        except (TypeError,ValueError): return None

    if "volume_liquidity_m5" not in out and observed("volume_m5") and observed("liquidity_usd"):
        vol,liq=f("volume_m5"),f("liquidity_usd")
        if vol is not None and liq is not None: out["volume_liquidity_m5"]=vol/max(1.0,liq)
    if "dex_buy_ratio_m5" not in out and observed("buys_m5") and observed("sells_m5"):
        buys,sells=f("buys_m5"),f("sells_m5")
        if buys is not None and sells is not None: out["dex_buy_ratio_m5"]=buys/max(1.0,buys+sells)

    if observed("price_change_m5") and observed("price_change_h1"):
        pc5,pch=f("price_change_m5"),f("price_change_h1")
        if pc5 is not None and pch is not None:
            out.setdefault("trend_alignment",pc5*pch); out.setdefault("short_vs_hour",pc5-(pch/12.0))
    if observed("buys_15") and observed("sells_15"):
        b15,s15=f("buys_15"),f("sells_15")
        if b15 is not None and s15 is not None: out.setdefault("flow_imbalance_15",(b15-s15)/max(1.0,b15+s15))
    if observed("buys_30") and observed("sells_30"):
        b30,s30=f("buys_30"),f("sells_30")
        if b30 is not None and s30 is not None:
            out.setdefault("flow_imbalance_30",(b30-s30)/max(1.0,b30+s30)); out.setdefault("activity_30",b30+s30)
    if observed("flow_imbalance_15") and observed("flow_imbalance_30"):
        out.setdefault("flow_shift",float(out["flow_imbalance_15"])-float(out["flow_imbalance_30"]))
    if observed("buys_h1") and observed("sells_h1"):
        bh,sh=f("buys_h1"),f("sells_h1")
        if bh is not None and sh is not None:
            out.setdefault("activity_h1",bh+sh); out.setdefault("flow_imbalance_h1",(bh-sh)/max(1.0,bh+sh))
    if observed("buys_15") and observed("prev_buys_15"):
        b15,prev=f("buys_15"),f("prev_buys_15")
        if b15 is not None and prev is not None: out.setdefault("buy_activity_change",(b15-prev)/max(1.0,prev))
    if observed("volume_h1") and observed("liquidity_usd"):
        vh,liq=f("volume_h1"),f("liquidity_usd")
        if vh is not None and liq is not None: out.setdefault("volume_liquidity_h1",vh/max(1.0,liq))
    if observed("fdv") and observed("liquidity_usd"):
        fdv,liq=f("fdv"),f("liquidity_usd")
        if fdv is not None and liq is not None: out.setdefault("fdv_liquidity_ratio",fdv/max(1.0,liq))
    if observed("market_cap") and observed("liquidity_usd"):
        mc,liq=f("market_cap"),f("liquidity_usd")
        if mc is not None and liq is not None: out.setdefault("marketcap_liquidity_ratio",mc/max(1.0,liq))
    try:
        from datetime import datetime
        ca=out.get("created_at"); pa=out.get("pair_created_at")
        if ca and pa:
            def _dt(v): return v if hasattr(v,"timestamp") else datetime.fromisoformat(str(v).replace("Z","+00:00"))
            out.setdefault("pair_age_hours",max(0.0,(_dt(ca)-_dt(pa)).total_seconds()/3600.0))
    except Exception:
        pass
    return out


def evaluate(population: list[dict], observations: list[dict]) -> dict:
    hits={genome_id(g):0 for g in population}
    for row in observations:
        obs=flatten(row)
        for g in population:
            if matches(g,obs): hits[genome_id(g)]+=1
    return {"ants":len(population),"observations":len(observations),"evaluations":len(population)*len(observations),
            "ants_with_hits":sum(v>0 for v in hits.values()),"total_hits":sum(hits.values()),"hits":hits}

def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("population"); p.add_argument("observations")
    a=p.parse_args()
    pop=json.load(open(a.population)); obs=json.load(open(a.observations))
    result=evaluate(pop,obs)
    result.pop("hits")
    print(json.dumps(result,indent=2,default=str))

if __name__ == "__main__": main()

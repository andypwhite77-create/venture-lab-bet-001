"""Replay archived V1 observations through a whole ant population."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from colony.evaluator import matches
from colony.genome import genome_id

def flatten(row: dict) -> dict:
    out = {}
    for field in ("features", "market"):
        value = row.get(field) or {}
        if isinstance(value, str):
            try: value=json.loads(value)
            except Exception: value={}
        out.update(value)
    out.update({k: row.get(k) for k in ("mint","created_at","entry_price")})
    liq=float(out.get("liquidity_usd") or 0); vol=float(out.get("volume_m5") or 0)
    out.setdefault("volume_liquidity_m5", vol/max(1.0,liq))
    buys=float(out.get("buys_m5") or 0); sells=float(out.get("sells_m5") or 0)
    out.setdefault("dex_buy_ratio_m5", buys/max(1.0,buys+sells))
    # Derived context sensors available from the observation itself. These add vocabulary
    # without peeking at future returns or sealed partitions.
    pc5=float(out.get("price_change_m5") or 0); pch=float(out.get("price_change_h1") or 0)
    b15=float(out.get("buys_15") or 0); s15=float(out.get("sells_15") or 0)
    b30=float(out.get("buys_30") or 0); s30=float(out.get("sells_30") or 0)
    out.setdefault("trend_alignment", pc5*pch)
    out.setdefault("short_vs_hour", pc5-(pch/12.0))
    out.setdefault("flow_imbalance_15", (b15-s15)/max(1.0,b15+s15))
    out.setdefault("flow_imbalance_30", (b30-s30)/max(1.0,b30+s30))
    out.setdefault("flow_shift", out["flow_imbalance_15"]-out["flow_imbalance_30"])
    out.setdefault("activity_30", b30+s30)
    bh=float(out.get("buys_h1") or 0); sh=float(out.get("sells_h1") or 0)
    vh=float(out.get("volume_h1") or 0); mc=float(out.get("market_cap") or 0); fdv=float(out.get("fdv") or 0)
    prev=float(out.get("prev_buys_15") or 0)
    out.setdefault("activity_h1", bh+sh)
    out.setdefault("flow_imbalance_h1", (bh-sh)/max(1.0,bh+sh))
    out.setdefault("buy_activity_change", (b15-prev)/max(1.0,prev))
    out.setdefault("volume_liquidity_h1", vh/max(1.0,liq))
    out.setdefault("fdv_liquidity_ratio", fdv/max(1.0,liq))
    out.setdefault("marketcap_liquidity_ratio", mc/max(1.0,liq))
    try:
        from datetime import datetime
        ca=out.get("created_at"); pa=out.get("pair_created_at")
        if ca and pa:
            def _dt(v):
                return v if hasattr(v,"timestamp") else datetime.fromisoformat(str(v).replace("Z","+00:00"))
            out.setdefault("pair_age_hours", max(0.0,(_dt(ca)-_dt(pa)).total_seconds()/3600.0))
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

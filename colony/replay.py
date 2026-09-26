"""Replay archived V1 observations through a whole ant population."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluator import matches
from genome import genome_id

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

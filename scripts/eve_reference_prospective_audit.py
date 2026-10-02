"""Prospective-only audit for frozen Eve reference ants v2.

Uses only assets first observed after the freeze timestamp. Historical folds are
never reused as proof, and pre-v10 Spartan answers are deliberately ignored.
"""
import asyncio, json, statistics, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db import init_db, connection
from colony.evaluator import matches
from colony.historical_nursery import load_rows, sampled_path_return_pct
from colony.paper_economics import TARGET_STAKE_GBP, measured_roundtrip_network_fee_sol, sol_gbp_rate
from colony.spartan_v2 import stress_returns, opportunity_efficiency, qualifies

FAMILY = "eve_reference_v2"
MIN_EVENTS = 25

async def main():
    await init_db()
    async with connection() as c:
        rec = await c.fetchrow("SELECT finalists,summary FROM historical_nursery_runs WHERE family=$1 ORDER BY created_at DESC LIMIT 1", FAMILY)
        first = await c.fetch("SELECT mint,min(created_at) first_seen FROM research_candidates GROUP BY mint")
        rows = await load_rows(c)
        fee = await measured_roundtrip_network_fee_sol(c)
    if not rec:
        raise SystemExit("eve_reference_v2 is not frozen")
    ants = rec['finalists']; ants = json.loads(ants) if isinstance(ants,str) else list(ants or [])
    summary = rec['summary']; summary = json.loads(summary) if isinstance(summary,str) else dict(summary or {})
    cutoff = float(summary['prospective_after'])
    first_seen = {r['mint']:r['first_seen'].timestamp() for r in first}
    prospective = [r for r in rows if first_seen.get(r['mint'],0) >= cutoff]
    rate,_ = sol_gbp_rate(); base = (fee*rate)/TARGET_STAKE_GBP
    results=[]
    for x in ants:
        g=x['genome']; obs=[]; universe={}; seen=set()
        for r in prospective:
            if r['mint'] in seen: continue
            seen.add(r['mint'])
            raw=sampled_path_return_pct(g,r['returns'])
            if raw is not None: universe[r['mint']]=raw/100.0
            if matches(g,r.get('flat') or {}) and raw is not None:
                obs.append((r['mint'],raw/100.0))
        rs=[v for _,v in obs]; taken={m for m,_ in obs}
        rejected=[v for m,v in universe.items() if m not in taken]
        expectation=statistics.fmean(rs) if rs else None
        positive=[v for v in rs if v>0]
        concentration=1.0 if not positive else max(positive)/max(sum(positive),1e-12)
        sufficient=len(rs)>=MIN_EVENTS
        row={'species':g.get('species'),'genome_id':x.get('genome_id'),'n':len(rs),'evidence_sufficient':sufficient,
             'mean_raw':expectation,'winner_concentration':concentration}
        if sufficient:
            stress=stress_returns(rs,base,500,seed='prospective-v2:'+x['genome_id'])
            eff=opportunity_efficiency(rs,rejected)
            row.update({'opportunity_efficiency':eff,'stress':stress.__dict__,
                        'qualification_pass':bool(qualifies(stress,expectation,eff,concentration))})
        results.append(row)
    out={'family':FAMILY,'prospective_after':cutoff,'prospective_rows':len(prospective),
         'prospective_unique_mints':len({r['mint'] for r in prospective}),
         'min_independent_events':MIN_EVENTS,'results':results}
    print(json.dumps(out,indent=2,default=str))

if __name__=='__main__':
    asyncio.run(main())

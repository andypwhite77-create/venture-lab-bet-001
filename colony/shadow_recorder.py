"""Persist counterfactual selection snapshots without changing the population."""
import json
from db import connection
from colony.selection_engine import shadow_plan

async def record(run_id):
    async with connection() as conn:
        run=await conn.fetchrow("SELECT population FROM colony_forward_runs WHERE run_id=$1",run_id)
        if not run:return {'recorded':False,'reason':'run_not_found'}
        pop=run['population'] if isinstance(run['population'],list) else json.loads(run['population'])
        cutoff=await conn.fetchval("SELECT COALESCE(max(candidate_id),0) FROM colony_forward_entries WHERE run_id=$1",run_id)
        # Shadow rank uses only matured, mint-deduplicated outcomes available at this cutoff.
        rows=await conn.fetch("""SELECT e.genome_id,e.family,count(DISTINCT e.mint) n,avg(o.net_return_pct) ret
          FROM colony_forward_entries e JOIN LATERAL (SELECT net_return_pct FROM research_outcomes
          WHERE candidate_id=e.candidate_id ORDER BY abs(horizon_minutes-e.hold_minutes) LIMIT 1) o ON true
          WHERE e.run_id=$1 AND e.candidate_id<=$2 GROUP BY e.genome_id,e.family""",run_id,cutoff)
        if not rows:return {'recorded':False,'reason':'no_matured_evidence'}
        ordered=sorted(rows,key=lambda r:float(r['ret']),reverse=True); total=len(ordered)
        counts={}; [counts.__setitem__(r['family'],counts.get(r['family'],0)+1) for r in ordered]
        ants=[]
        for i,r in enumerate(ordered): ants.append({'id':r['genome_id'],'family':r['family'],
          'rank_fraction':i/max(1,total-1),'evidence_n':int(r['n']),'mean_return_pct':float(r['ret'])})
        plan=shadow_plan(ants,{k:v/total for k,v in counts.items()})
        pid=await conn.fetchval("""INSERT INTO colony_shadow_plans(run_id,evidence_cutoff,plan)
          VALUES($1,$2,$3::jsonb) ON CONFLICT(run_id,evidence_cutoff) DO NOTHING RETURNING id""",
          run_id,cutoff,json.dumps(plan))
        return {'recorded':bool(pid),'plan_id':pid,'evidence_cutoff':cutoff,
                'breeders':len(plan['breeders']),'replace':len(plan['replace'])}

"""Turn matured sensory history into candidate niche hypotheses."""
from db import connection
from colony.niche_discovery import discover

def flatten(candidate,sense,ret):
    def obj(x):
        import json
        return x if isinstance(x,dict) else json.loads(x or '{}')
    f=obj(candidate.get('features')); m=obj(candidate.get('market')); snap=obj(sense)
    row={'return_pct':float(ret),'source_count':snap.get('source_count',0),
         'price_disagreement_ratio':snap.get('price_disagreement_ratio',0)}
    for prefix,data in (('f',f),('m',m)):
        for k,v in data.items():
            if isinstance(v,(int,float,bool)): row[f'{prefix}_{k}']=v
    return row

async def candidates(run_id,min_n=12,min_effect=5.0):
    async with connection() as conn:
        rows=await conn.fetch("""SELECT c.features,c.market,s.snapshot,o.net_return_pct
          FROM research_candidates c JOIN colony_sensory_snapshots s ON s.candidate_id=c.id
          JOIN LATERAL (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=c.id ORDER BY horizon_minutes DESC LIMIT 1) o ON true
          WHERE EXISTS(SELECT 1 FROM colony_forward_entries e WHERE e.run_id=$1 AND e.candidate_id=c.id)
          ORDER BY c.id""",run_id)
    data=[flatten(dict(r),r['snapshot'],r['net_return_pct']) for r in rows]
    return {'matured_sensory_rows':len(data),'candidate_niches':discover(data,min_n,min_effect)[:20]}

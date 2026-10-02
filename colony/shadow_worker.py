"""Expose counterfactual descendants only to candidates after their birth cutoff."""
import json
from db import connection
from colony.forward import eligible

PROGRESS_KEY='shadow_descendants:global'

async def process_shadow():
    async with connection() as conn:
        await conn.execute("""CREATE TABLE IF NOT EXISTS colony_candidate_progress(
          stream_key TEXT PRIMARY KEY,last_candidate_id BIGINT NOT NULL DEFAULT 0,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
        kids=await conn.fetch("""SELECT d.id,d.genome,p.evidence_cutoff FROM colony_shadow_descendants d
          JOIN colony_shadow_plans p ON p.id=d.shadow_plan_id WHERE d.state='counterfactual'""")
        if not kids:
            return {'descendants':0,'candidates_considered':0,'inserted':0}
        last=await conn.fetchval("SELECT last_candidate_id FROM colony_candidate_progress WHERE stream_key=$1",PROGRESS_KEY)
        if last is None:
            last=min(int(k['evidence_cutoff'] or 0) for k in kids)
            await conn.execute("INSERT INTO colony_candidate_progress(stream_key,last_candidate_id) VALUES($1,$2) ON CONFLICT DO NOTHING",PROGRESS_KEY,last)
        rows=await conn.fetch("SELECT id,created_at,mint,features,market FROM research_candidates WHERE id>$1 ORDER BY id",int(last))
        if not rows:
            return {'descendants':len(kids),'candidates_considered':0,'inserted':0}
        kid_ids=[k['id'] for k in kids]
        latest_rows=await conn.fetch("""SELECT shadow_descendant_id,mint,max(observed_at) AS observed_at
          FROM colony_shadow_entries WHERE shadow_descendant_id=ANY($1::bigint[])
          GROUP BY shadow_descendant_id,mint""",kid_ids)
        latest={(r['shadow_descendant_id'],r['mint']):r['observed_at'] for r in latest_rows}
        inserted=0; considered=0
        for k in kids:
            g=k['genome'] if isinstance(k['genome'],dict) else json.loads(k['genome'])
            cutoff=int(k['evidence_cutoff'] or 0)
            for row in rows:
                if row['id']<=cutoff: continue
                considered+=1; r=dict(row); key=(k['id'],r['mint']); prev=latest.get(key)
                if not eligible(g,r,prev):continue
                hold=int(g.get('parameters',{}).get('hold_minutes',15))
                x=await conn.execute("""INSERT INTO colony_shadow_entries(shadow_descendant_id,mint,candidate_id,observed_at,hold_minutes)
                  VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING""",k['id'],r['mint'],r['id'],r['created_at'],hold)
                if x.endswith('1'):
                    inserted+=1; latest[key]=r['created_at']
        await conn.execute("UPDATE colony_candidate_progress SET last_candidate_id=$2,updated_at=now() WHERE stream_key=$1",PROGRESS_KEY,rows[-1]['id'])
        return {'descendants':len(kids),'candidates_considered':considered,'inserted':inserted}

"""Expose counterfactual descendants only to candidates after their birth cutoff."""
import json
from db import connection
from colony.forward import eligible

async def process_shadow():
    async with connection() as conn:
        kids=await conn.fetch("""SELECT d.id,d.genome,p.evidence_cutoff FROM colony_shadow_descendants d
          JOIN colony_shadow_plans p ON p.id=d.shadow_plan_id WHERE d.state='counterfactual'""")
        inserted=0
        for k in kids:
            g=k['genome'] if isinstance(k['genome'],dict) else json.loads(k['genome'])
            rows=await conn.fetch("SELECT id,created_at,mint,features,market FROM research_candidates WHERE id>$1 ORDER BY id",k['evidence_cutoff'])
            for row in rows:
                r=dict(row); prev=await conn.fetchval("SELECT max(observed_at) FROM colony_shadow_entries WHERE shadow_descendant_id=$1 AND mint=$2",k['id'],r['mint'])
                if not eligible(g,r,prev):continue
                hold=int(g.get('parameters',{}).get('hold_minutes',15))
                x=await conn.execute("""INSERT INTO colony_shadow_entries(shadow_descendant_id,mint,candidate_id,observed_at,hold_minutes)
                  VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING""",k['id'],r['mint'],r['id'],r['created_at'],hold)
                inserted+=int(x.endswith('1'))
        return {'descendants':len(kids),'inserted':inserted}

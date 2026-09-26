"""Resolve Queen memories only from prospective experimental outcomes."""
import json
from db import connection

async def reconcile_selection(run_id,min_future=20,edge_pp=1.0):
    from colony.shadow_replay import audit_plan
    async with connection() as c:
        plans=await c.fetch("SELECT id FROM colony_shadow_plans WHERE run_id=$1 ORDER BY id",run_id)
    resolved=[]
    for p in plans:
        a=await audit_plan(p['id']); n=a.get('future_rows',0); edge=a.get('selection_future_edge_pct')
        if n<min_future or edge is None: continue
        outcome='supported' if edge>=edge_pp else ('contradicted' if edge<=-edge_pp else 'inconclusive')
        lesson=f"Shadow selection plan {p['id']} future edge {edge:+.4f}pp across {n} future rows: {outcome}."
        confidence=min(.95,.5+n/200)
        async with connection() as c:
            exists=await c.fetchval("SELECT 1 FROM colony_mind_memory WHERE run_id=$1 AND subject=$2",run_id,f'selection_plan:{p["id"]}')
            if not exists:
                await c.execute('''INSERT INTO colony_mind_memory(run_id,kind,subject,lesson,evidence,confidence,outcome)
                  VALUES($1,'prospective_lesson',$2,$3,$4::jsonb,$5,$6)''',run_id,f'selection_plan:{p["id"]}',lesson,json.dumps(a),confidence,outcome)
                resolved.append({'plan_id':p['id'],'outcome':outcome,'edge':edge,'n':n})
    return resolved

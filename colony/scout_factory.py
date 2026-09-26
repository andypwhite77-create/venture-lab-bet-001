"""Creates quarantined paper scouts only from already-approved proposals."""
import json
from db import connection

async def materialize_eligible():
    async with connection() as conn:
        rows=await conn.fetch("""SELECT p.id,p.run_id,p.proposal FROM colony_proposals p
          LEFT JOIN colony_scout_experiments s ON s.proposal_id=p.id
          WHERE p.proposal_type='scout_experiment' AND p.status='approved' AND s.id IS NULL
          ORDER BY p.id LIMIT 5""")
        made=[]
        for r in rows:
            spec=r['proposal'] if isinstance(r['proposal'],dict) else json.loads(r['proposal'])
            constraints=spec.get('constraints',{})
            if not constraints.get('paper_only') or constraints.get('max_scouts',99)>5:
                continue
            # Deliberately no genome generation yet: approval cannot silently invent tactics.
            sid=await conn.fetchval("""INSERT INTO colony_scout_experiments
              (proposal_id,run_id,genome_ids,evidence) VALUES($1,$2,'[]'::jsonb,$3::jsonb) RETURNING id""",
              r['id'],r['run_id'],json.dumps(spec.get('evidence_at_proposal',{})))
            made.append(sid)
    return {'materialized':made,'count':len(made)}

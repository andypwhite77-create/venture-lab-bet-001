"""Persist point-in-time shared senses once per new research candidate."""
import json, time
from db import connection
from colony.sensors import snapshot

async def process_senses(limit=20):
    async with connection() as conn:
        rows=await conn.fetch("""SELECT c.id,c.mint FROM research_candidates c
          LEFT JOIN colony_sensory_snapshots s ON s.candidate_id=c.id
          WHERE s.id IS NULL ORDER BY c.id DESC LIMIT $1""",limit)
        done=0
        for row in reversed(rows):
            t=time.monotonic(); snap=await snapshot(row['mint'])
            latency=int((time.monotonic()-t)*1000)
            await conn.execute("""INSERT INTO colony_sensory_snapshots
              (candidate_id,mint,source_count,disagreement_ratio,snapshot)
              VALUES($1,$2,$3,$4,$5::jsonb) ON CONFLICT(candidate_id) DO NOTHING""",
              row['id'],row['mint'],snap['source_count'],snap['price_disagreement_ratio'],json.dumps(snap))
            for src in snap['sources']:
                await conn.execute("""INSERT INTO colony_provider_health(provider,ok,latency_ms,error)
                  VALUES($1,$2,$3,$4)""",src['provider'],bool(src.get('ok')),latency,src.get('error'))
            done+=1
        return {'snapshots':done}

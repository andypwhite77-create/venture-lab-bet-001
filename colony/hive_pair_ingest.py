"""Conservative research-only prospective pair ingestion.

Pairs only real, recorded forward tournament decisions on identical candidates.
Challenger must bear explicit loss-tail species tag; control must be baseline.
Independent horizon outcomes must exist for both and occur after experiment start.
This does not turn historical nursery genomes into deployed forward entrants.
"""
import asyncio,json
from db import init_db,connection
from colony.hive_forward_scoreboard import SCHEMA
# Illustrative allowance for each paper round trip; measured fills are unavailable.
FRICTION_PCT=0.30
SQL="""WITH entries AS (
 SELECT e.run_id,e.genome_id,e.candidate_id,e.observed_at,e.hold_minutes,
        a.baseline,a.genome->>'species' species
 FROM family_tournament_entries e JOIN family_tournament_ants a USING(run_id,genome_id)
 UNION ALL
 SELECT e.run_id,e.genome_id,e.candidate_id,e.observed_at,e.hold_minutes,
        a.baseline,a.genome->>'species' species
 FROM reversal_tournament_entries e JOIN reversal_tournament_ants a USING(run_id,genome_id)
)
SELECT DISTINCT ON(c.run_id,c.genome_id,b.genome_id,c.candidate_id)
 c.run_id,c.genome_id challenger_id,b.genome_id control_id,c.candidate_id,
 greatest(c.observed_at,b.observed_at) observed_at,
 oc.net_return_pct challenger_raw,ob.net_return_pct control_raw
 FROM entries c JOIN entries b
  ON b.run_id=c.run_id AND b.candidate_id=c.candidate_id
  AND b.genome_id<>c.genome_id AND b.baseline=true
 JOIN research_outcomes oc ON oc.candidate_id=c.candidate_id AND oc.horizon_minutes=c.hold_minutes
 JOIN research_outcomes ob ON ob.candidate_id=b.candidate_id AND ob.horizon_minutes=b.hold_minutes
 WHERE c.species='loss_tail_challenger' AND c.baseline=false
 AND c.observed_at>$1 AND b.observed_at>$1
 AND oc.net_return_pct IS NOT NULL AND ob.net_return_pct IS NOT NULL
 ORDER BY c.run_id,c.genome_id,b.genome_id,c.candidate_id,c.observed_at DESC LIMIT 1000"""
async def run():
 await init_db();out=[]
 async with connection() as conn:
  await conn.execute(SCHEMA)
  experiments=await conn.fetch("SELECT id,created_at FROM hive_experiments WHERE status='awaiting_prospective_test'")
  for ex in experiments:
   rows=await conn.fetch(SQL,ex['created_at']);inserted=0
   for x in rows:
    # Mark as an indicative paper paired estimate, not realised trade P&L.
    result=await conn.fetchval("""INSERT INTO hive_forward_pairs
      (experiment_id,opportunity_id,observed_at,challenger_genome_id,
       control_genome_id,challenger_net_pct,control_net_pct,source)
      VALUES($1,$2,$3,$4,$5,$6,$7,'forward_shadow')
      ON CONFLICT DO NOTHING RETURNING id""",
      ex['id'],str(x['run_id'])+':'+str(x['candidate_id']),x['observed_at'],
      x['challenger_id'],x['control_id'],
      float(x['challenger_raw'])-FRICTION_PCT,float(x['control_raw'])-FRICTION_PCT)
    inserted+=bool(result)
   out.append({'experiment_id':ex['id'],'source_eligible':len(rows),'inserted':inserted,
     'caveat':'estimated 30 bps round-trip friction; not executable P&L'})
 return out
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

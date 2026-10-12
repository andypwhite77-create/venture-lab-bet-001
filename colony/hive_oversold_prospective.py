"""Frozen prospective selector audit, no execution or Spartan permissions."""
import asyncio,json,statistics
from datetime import timedelta
from db import init_db,connection
from colony.hive_exit_path_audit import simulate
RUN='reversal-novelty-study-v1'
STUDY='oversold-selection-v1'
def evaluate(rows,minimum=30):
 valid=[r for r in rows if r['status']=='observed_path']
 accepted=[r['net_pct'] for r in valid if r['selected']]
 rejected=[r['net_pct'] for r in valid if not r['selected']]
 return {'complete':len(valid),'excluded':len(rows)-len(valid),'accepted':len(accepted),'rejected':len(rejected),
  'accepted_avg':statistics.fmean(accepted) if accepted else None,
  'rejected_avg':statistics.fmean(rejected) if rejected else None,
  'edge':statistics.fmean(accepted)-statistics.fmean(rejected) if accepted and rejected else None,
  'status':'descriptive_only' if len(accepted)>=minimum and len(rejected)>=minimum else 'insufficient_evidence'}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute("""CREATE TABLE IF NOT EXISTS hive_selection_studies(
  name TEXT PRIMARY KEY,started_at TIMESTAMPTZ NOT NULL DEFAULT now(),config JSONB NOT NULL)""")
  await c.execute("INSERT INTO hive_selection_studies(name,config) VALUES($1,$2::jsonb) ON CONFLICT DO NOTHING",
   STUDY,json.dumps({'run':RUN,'selector':'oversold_rebound','control':'observation_control',
    'hold_minutes':15,'friction_bps':30,'minimum_per_group':30,'research_only':True}))
  started=await c.fetchval("SELECT started_at FROM hive_selection_studies WHERE name=$1",STUDY)
  records=await c.fetch("""SELECT e.candidate_id,e.observed_at,e.hold_minutes,
   a.genome->>'species' species,r.entry_price
   FROM family_tournament_entries e JOIN family_tournament_ants a USING(run_id,genome_id)
   JOIN research_candidates r ON r.id=e.candidate_id
   WHERE e.run_id=$1 AND e.observed_at>$2 AND a.genome->>'species' IN ('oversold_rebound','observation_control')""",RUN,started)
  selected={r['candidate_id'] for r in records if r['species']=='oversold_rebound'}
  controls={r['candidate_id']:r for r in records if r['species']=='observation_control'}
  outcomes=[]
  for cid,r in controls.items():
   samples=await c.fetch("""SELECT observed_at,price FROM research_price_path
    WHERE candidate_id=$1 AND observed_at>=$2 AND observed_at<=$3 ORDER BY observed_at""",
    cid,r['observed_at'],r['observed_at']+timedelta(minutes=r['hold_minutes']))
   result=simulate(r['observed_at'],float(r['entry_price'] or 0),
    [(x['observed_at'],x['price']) for x in samples],r['hold_minutes'])
   outcomes.append({'candidate_id':cid,'selected':cid in selected,**result})
  return {'study':STUDY,'started_at':started.isoformat(),'opportunities':len(controls),
   **evaluate(outcomes),'caveat':'sampled paper quotes, estimated friction, no causal or live claim',
   'permission':'none'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

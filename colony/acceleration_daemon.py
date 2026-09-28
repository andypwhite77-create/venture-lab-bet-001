"""Periodic evolutionary accelerator. Runs only after enough genuinely new mints arrive."""
import asyncio,json,logging
from db import init_db,connection
from colony.historical_nursery import FAMILIES,run_family
from colony.surrogate_breeder import run_all as guided_all
from colony.pattern_discovery import discover
from colony.continuous_evolution import seed_queue_from_latest_nursery
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
MIN_NEW_MINTS=25
SLEEP_SECONDS=21600
async def cycle():
 async with connection() as c:
  current=await c.fetchval('''SELECT count(DISTINCT c.mint) FROM research_candidates c
    WHERE EXISTS(SELECT 1 FROM research_outcomes o WHERE o.candidate_id=c.id AND o.net_return_pct IS NOT NULL)''')
  state=await c.fetchval("SELECT value FROM acceleration_state WHERE key='historical_nursery'")
  state=json.loads(state) if isinstance(state,str) else (state or {})
  last=int(state.get('unique_mints',current))
  if not state:
   await c.execute("INSERT INTO acceleration_state(key,value) VALUES('historical_nursery',$1::jsonb) ON CONFLICT(key) DO NOTHING",json.dumps({'unique_mints':current}))
   return {'status':'baseline_set','unique_mints':current}
  if current-last<MIN_NEW_MINTS:return {'status':'waiting','unique_mints':current,'new_mints':current-last,'needed':MIN_NEW_MINTS}
  summaries=[]
  for fam in FAMILIES:
   r=await run_family(c,fam,10000); finalists=r.pop('finalists')
   await c.execute('''INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary)
    VALUES($1,$2,$3,$4::jsonb,$5::jsonb)''',fam,r['tested'],r['rows'],json.dumps(finalists),json.dumps(r,default=str))
   summaries.append({k:v for k,v in r.items() if k!='best'})
  guided=await guided_all(c)
  patterns=await discover(c,30)
  for x in patterns['top']:
   await c.execute('INSERT INTO discovered_patterns(rule,robust_score,evidence) VALUES($1::jsonb,$2,$3::jsonb)',json.dumps(x['rule']),x['robust_score'],json.dumps(x,default=str))
  queued=await seed_queue_from_latest_nursery(c)
  await c.execute("UPDATE acceleration_state SET value=$1::jsonb,updated_at=now() WHERE key='historical_nursery'",json.dumps({'unique_mints':current}))
  return {'status':'evolved','unique_mints':current,'new_mints':current-last,'nurseries':summaries,'guided':guided,'patterns_positive':patterns['positive_robust'],'queued':queued}
async def main():
 await init_db()
 while True:
  try:logging.info('acceleration %s',await cycle())
  except Exception:logging.exception('acceleration_error')
  await asyncio.sleep(SLEEP_SECONDS)
if __name__=='__main__':asyncio.run(main())

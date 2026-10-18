"""Frozen forward-only exit comparison, read-only and not execution evidence.
Registration timestamp freezes admission; outcomes are append-only and exclude missing paths.
"""
import asyncio,json
from db import init_db,connection
from colony.hive_exit_path_audit import simulate
TRIAL='exit-policy-prospective-v1'
HOLD_MIN=60
POLICIES={'control':(None,None),'take_10':(None,10),'stop_10_take_15':(-10,15)}
SCHEMA='''CREATE TABLE IF NOT EXISTS prospective_exit_trials(
 trial text PRIMARY KEY,started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 hold_minutes integer NOT NULL,policies jsonb NOT NULL,
 authority text NOT NULL DEFAULT 'observation_only');
 CREATE TABLE IF NOT EXISTS prospective_exit_trial_results(
 trial text NOT NULL REFERENCES prospective_exit_trials(trial),candidate_id bigint NOT NULL,
 evaluated_at timestamptz NOT NULL DEFAULT clock_timestamp(),entry_at timestamptz NOT NULL,
 outcome jsonb NOT NULL,PRIMARY KEY(trial,candidate_id));'''
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  await c.execute('''INSERT INTO prospective_exit_trials(trial,hold_minutes,policies)
  VALUES($1,$2,$3::jsonb) ON CONFLICT DO NOTHING''',TRIAL,HOLD_MIN,json.dumps(POLICIES))
  trial=await c.fetchrow('SELECT started_at,hold_minutes,policies FROM prospective_exit_trials WHERE trial=$1',TRIAL)
  rows=await c.fetch('''SELECT r.id,r.created_at,r.entry_price,r.market
   FROM research_candidates r WHERE r.created_at >= $1
   AND r.created_at <= now()-interval '90 minutes'
   AND NOT EXISTS(SELECT 1 FROM prospective_exit_trial_results t WHERE t.trial=$2 AND t.candidate_id=r.id)
   ORDER BY r.id LIMIT 100''',trial['started_at'],TRIAL)
  saved=0;excluded=0
  for r in rows:
   market=r['market'];market=json.loads(market) if isinstance(market,str) else dict(market or {})
   path=await c.fetch('''SELECT observed_at,price FROM research_price_path
    WHERE candidate_id=$1 AND observed_at>=$2 AND observed_at<=$2+interval '60 minutes'
    AND quality='fresh_fetch' ORDER BY observed_at''',r['id'],r['created_at'])
   samples=[(x['observed_at'],x['price']) for x in path]
   allowed=r['entry_price'] is not None and float(r['entry_price'])>0 and market.get('price_evidence')!='discovery_only_no_provider_tick_timestamp'
   if not allowed:
    outcomes={'excluded':'unverified_or_missing_entry'};excluded+=1
   else:
    outcomes={name:simulate(r['created_at'],float(r['entry_price']),samples,HOLD_MIN,stop_pct=stop,take_pct=take) for name,(stop,take) in POLICIES.items()}
    if any(v['status']!='observed_path' for v in outcomes.values()):excluded+=1
   result=await c.execute('''INSERT INTO prospective_exit_trial_results(trial,candidate_id,entry_at,outcome)
      VALUES($1,$2,$3,$4::jsonb) ON CONFLICT DO NOTHING''',TRIAL,r['id'],r['created_at'],json.dumps(outcomes))
   saved+=int(result.endswith('1'))
  total=await c.fetchval('SELECT count(*) FROM prospective_exit_trial_results WHERE trial=$1',TRIAL)
  return {'trial':TRIAL,'started_at':trial['started_at'].isoformat(),'new_results':saved,'new_exclusions':excluded,'total_results':total,'authority':'prospective_sampled_marks_no_fills_no_live'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

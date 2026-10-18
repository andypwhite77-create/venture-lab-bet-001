"""Frozen, prospective Queen feature-pair confirmation on later verified 60m outcomes.
Observational only; never execution, Spartan evidence, or automatic promotion.
"""
import asyncio,json,math
from db import init_db,connection
from colony.entry_failure_lab import FIELDS,_num,_obj
SCHEMA='''CREATE TABLE IF NOT EXISTS queen_forward_confirmations(
 id bigserial PRIMARY KEY,queen text NOT NULL,pair_key text NOT NULL,
 registered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 features jsonb NOT NULL, directions jsonb NOT NULL, thresholds jsonb NOT NULL,
 source_pair_id bigint NOT NULL UNIQUE, authority text NOT NULL DEFAULT 'research_only');
CREATE TABLE IF NOT EXISTS queen_forward_confirmation_results(
 confirmation_id bigint NOT NULL REFERENCES queen_forward_confirmations(id),
 candidate_id bigint NOT NULL, observed_at timestamptz NOT NULL,
 selected boolean, net_pct double precision, reason text NOT NULL,
 PRIMARY KEY(confirmation_id,candidate_id));'''

def classify(features, directions, thresholds, entry):
 values=[_num(_obj(entry).get(x)) for x in features]
 if any(v is None for v in values):return None
 return all(v>float(t) if d=='high' else v<=float(t) for v,d,t in zip(values,directions,thresholds))
async def register(conn,pair_id):
 pair=await conn.fetchrow('SELECT id,queen,pair_key,result FROM queen_pair_hypotheses WHERE id=$1',pair_id)
 if pair is None:raise ValueError('unknown_pair')
 data=_obj(pair['result']);features=data.get('features');directions=data.get('directions');thresholds=data.get('training_thresholds')
 if data.get('status')!='exploratory_only' or not all(isinstance(x,list) and len(x)==2 for x in (features,directions,thresholds)):raise ValueError('unqualified_discovery')
 if features[0]==features[1] or any(f not in FIELDS for f in features) or any(d not in ('high','low') for d in directions) or any(_num(t) is None for t in thresholds):raise ValueError('invalid_frozen_rule')
 return await conn.fetchrow('''INSERT INTO queen_forward_confirmations(queen,pair_key,features,directions,thresholds,source_pair_id)
 VALUES($1,$2,$3::jsonb,$4::jsonb,$5::jsonb,$6) ON CONFLICT(source_pair_id) DO NOTHING RETURNING id,registered_at''',pair['queen'],pair['pair_key'],json.dumps(features),json.dumps(directions),json.dumps(thresholds),pair_id)
async def collect(conn):
 # The outcome must have been generated after registration, from a candidate born after registration.
 return await conn.execute('''INSERT INTO queen_forward_confirmation_results(confirmation_id,candidate_id,observed_at,selected,net_pct,reason)
 SELECT f.id,c.id,o.measured_at,
 CASE WHEN (c.features ? (f.features->>0)) AND (c.features ? (f.features->>1))
  AND jsonb_typeof(c.features->(f.features->>0))='number' AND jsonb_typeof(c.features->(f.features->>1))='number'
  THEN (((c.features->>(f.features->>0))::float8 > (f.thresholds->>0)::float8) = ((f.directions->>0)='high'))
    AND (((c.features->>(f.features->>1))::float8 > (f.thresholds->>1)::float8) = ((f.directions->>1)='high')) ELSE NULL END,
 o.net_return_pct,'prospective_horizon_mark_not_fill'
 FROM queen_forward_confirmations f JOIN research_candidates c ON c.created_at>f.registered_at
 JOIN research_outcomes o ON o.candidate_id=c.id AND o.horizon_minutes=60
 WHERE o.measured_at>f.registered_at AND o.net_return_pct IS NOT NULL
 AND NOT EXISTS (SELECT 1 FROM queen_forward_confirmation_results old WHERE old.confirmation_id=f.id AND old.candidate_id=c.id)
 ON CONFLICT DO NOTHING''')
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  added=await collect(c)
  groups=await c.fetch('''SELECT confirmation_id,count(*) n,count(*) FILTER(WHERE selected) selected_n,
 count(*) FILTER(WHERE selected=false) other_n,
 avg(net_pct) FILTER(WHERE selected) selected_mean,
 avg(net_pct) FILTER(WHERE selected=false) other_mean
 FROM queen_forward_confirmation_results GROUP BY confirmation_id ORDER BY confirmation_id''')
 return {'inserted':added,'groups':[dict(x) for x in groups],'authority':'forward_observational_only_no_live'}
async def register_pair(pair_id):
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  value=await register(c,pair_id)
 return {'registered':dict(value) if value else None,'authority':'prospective_only_no_promotion'}
if __name__=='__main__':
 import sys
 if len(sys.argv)==3 and sys.argv[1]=='register':print(json.dumps(asyncio.run(register_pair(int(sys.argv[2]))),default=str))
 elif len(sys.argv)==1:print(json.dumps(asyncio.run(run()),default=str))
 else:raise SystemExit('usage: python -m colony.queen_forward_confirmation [register PAIR_ID]')

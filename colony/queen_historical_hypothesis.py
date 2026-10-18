"""Bounded historical hypothesis engine: whitelisted entry feature, mint-separated chronological holdout.
Research only. Neither history nor this result grants promotion or execution authority.
"""
import asyncio,json,math,statistics
from db import init_db,connection
from colony.entry_failure_lab import FIELDS,_num,_obj
SCHEMA='''CREATE TABLE IF NOT EXISTS queen_historical_hypotheses(
 id bigserial PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 queen text NOT NULL, feature text NOT NULL, direction text NOT NULL,
 result jsonb NOT NULL, evidence_class text NOT NULL DEFAULT 'historical_discovery_only');'''

def test(rows,feature,direction):
 if feature not in FIELDS or direction not in ('high','low'):raise ValueError('invalid hypothesis')
 grouped={}
 for r in sorted(rows,key=lambda x:(x['created_at'],x['candidate_id'])):
  mint=str(r['mint']);f=_num(_obj(r['features']).get(feature));y=_num(r['net_return_pct'])
  if f is None or y is None:continue
  grouped.setdefault(mint,[]).append((f,y))
 mints=list(grouped);cut=int(len(mints)*.7)
 if cut<5 or len(mints)-cut<3:return {'status':'insufficient_independent_mints','mints':len(mints)}
 train=[v for mint in mints[:cut] for v in grouped[mint]]
 threshold=statistics.median(v for v,_ in train)
 def measure(part):
  selected=[y for mint in part for v,y in grouped[mint] if (v>threshold if direction=='high' else v<=threshold)]
  rejected=[y for mint in part for v,y in grouped[mint] if (v<=threshold if direction=='high' else v>threshold)]
  return {'selected_n':len(selected),'other_n':len(rejected),'selected_mean_pct':round(statistics.mean(selected),4) if selected else None,'other_mean_pct':round(statistics.mean(rejected),4) if rejected else None,'distinct_mints':len(part)}
 return {'status':'historical_discovery_only','feature':feature,'direction':direction,'training_mints':cut,'holdout_mints':len(mints)-cut,'training_median':threshold,'training':measure(mints[:cut]),'chronological_mint_holdout':measure(mints[cut:]),'no_promotion':True,'limitations':'Repeated candidates per mint are correlated; holdout reused across proposals is no longer independent; archived returns are not fills.'}
async def run(queen,feature,direction):
 if feature not in FIELDS or direction not in ('high','low') or not queen or len(queen)>80:raise ValueError('invalid proposal')
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  rows=await c.fetch('''SELECT c.id candidate_id,c.created_at,c.mint,c.features,o.net_return_pct
   FROM research_candidates c JOIN research_outcomes o ON o.candidate_id=c.id
   WHERE o.horizon_minutes=60 AND o.net_return_pct IS NOT NULL ORDER BY c.created_at,c.id''')
  result=test(rows,feature,direction)
  await c.execute('INSERT INTO queen_historical_hypotheses(queen,feature,direction,result) VALUES($1,$2,$3,$4::jsonb)',queen,feature,direction,json.dumps(result))
 return {'queen':queen,'result':result,'authority':'hypothesis_discovery_only_no_live'}
if __name__=='__main__':
 import sys
 if len(sys.argv)!=4:raise SystemExit('usage: python -m colony.queen_historical_hypothesis QUEEN FEATURE high|low')
 print(json.dumps(asyncio.run(run(*sys.argv[1:]))))

"""Bounded two-feature historical discovery; mint-isolated chronological partition.
No examination data, fills, promotions, or trading authority.
"""
import asyncio,json,statistics
from db import init_db,connection
from colony.entry_failure_lab import FIELDS,_obj,_num
from colony.simple_killer_gate import assess as simple_screen

def evaluate(rows,f1,d1,f2,d2):
 if f1 not in FIELDS or f2 not in FIELDS or f1==f2 or d1 not in ('high','low') or d2 not in ('high','low'):raise ValueError('unapproved_pair')
 grouped={}
 for r in sorted(rows,key=lambda x:(x['created_at'],x['candidate_id'])):
  feat=_obj(r['features']);a=_num(feat.get(f1));b=_num(feat.get(f2));y=_num(r['net_return_pct'])
  if None in (a,b,y):continue
  grouped.setdefault(str(r['mint']),[]).append((a,b,y))
 mints=list(grouped);n=int(len(mints)*.7)
 if n<20 or len(mints)-n<10:return {'status':'insufficient_independent_mints','mints':len(mints)}
 train=[v for mint in mints[:n] for v in grouped[mint]]
 cut1=statistics.median(v[0] for v in train);cut2=statistics.median(v[1] for v in train)
 def metric(part):
  selected=[];other=[];selected_mints=set()
  for mint in part:
   for a,b,y in grouped[mint]:
    passes=(a>cut1 if d1=='high' else a<=cut1) and (b>cut2 if d2=='high' else b<=cut2)
    if passes:selected.append(y);selected_mints.add(mint)
    else:other.append(y)
  return {'selected_n':len(selected),'other_n':len(other),'selected_mints':len(selected_mints),'selected_mean_pct':round(statistics.mean(selected),4) if selected else None,'other_mean_pct':round(statistics.mean(other),4) if other else None,
          'economic_screen':simple_screen(selected,selected+other,len(selected_mints))}
 training=metric(mints[:n]);later=metric(mints[n:])
 status='research_screen_passed_not_independent' if training['economic_screen']['passes_screen'] and later['economic_screen']['passes_screen'] else 'economically_rejected'
 return {'status':status,'features':[f1,f2],'directions':[d1,d2],'training_mints':n,'later_mints':len(mints)-n,'training_thresholds':[cut1,cut2],'training':training,'later':later,'promotion_allowed':False,'warning':'Historical holdout reused by research; not independent proof.'}
async def run(queen,f1,d1,f2,d2):
 if not queen or len(queen)>80:raise ValueError('bad_queen')
 await init_db()
 async with connection() as c:
  rows=await c.fetch('''SELECT c.id candidate_id,c.created_at,c.mint,c.features,o.net_return_pct FROM research_candidates c JOIN research_outcomes o ON o.candidate_id=c.id WHERE o.horizon_minutes=60 AND o.net_return_pct IS NOT NULL ORDER BY c.created_at,c.id''')
  result=evaluate(rows,f1,d1,f2,d2)
  await c.execute('''CREATE TABLE IF NOT EXISTS queen_pair_hypotheses(id bigserial PRIMARY KEY,queen text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),pair_key text NOT NULL UNIQUE,result jsonb NOT NULL)''')
  key='|'.join(sum(([f,d] for f,d in sorted(((f1,d1),(f2,d2)))),[]))
  inserted=await c.execute('INSERT INTO queen_pair_hypotheses(queen,pair_key,result) VALUES($1,$2,$3::jsonb) ON CONFLICT DO NOTHING',queen,key,json.dumps(result))
 return {'stored':inserted.endswith('1'),'result':result,'authority':'historical_discovery_only'}
if __name__=='__main__':
 import sys
 if len(sys.argv)!=6:raise SystemExit('usage QUEEN FEATURE DIR FEATURE DIR')
 print(json.dumps(asyncio.run(run(*sys.argv[1:]))))

"""Bounded paired founder/descendant research, no promotion or trading.
Only training and validation are evaluated; sealed holdout remains untouched.
"""
import asyncio,copy,json,random
from db import init_db,connection
from colony.historical_nursery import founders,load_rows,split_rows,evaluate
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate

SCHEMA='''CREATE TABLE IF NOT EXISTS queen_targeted_descendant_runs(id bigserial primary key,
 created_at timestamptz not null default clock_timestamp(),family text not null,
 result jsonb not null);'''

def score(parts):
 t,v=parts
 if min(t.get('n',0),v.get('n',0))<25:return -1000.0
 a=float(t.get('avg_net_gbp') or -100);b=float(v.get('avg_net_gbp') or -100)
 med=min(float(t.get('median_return_pct') or -100),float(v.get('median_return_pct') or -100))
 return round(min(a,b)+0.01*med,5)

def descendants(founder,seed=20261020,n=64):
 rng=random.Random(seed);p=founder['parameters'];out=[]
 for _ in range(n):
  g=copy.deepcopy(founder);g['parameters']=dict(p)
  keys=[k for k in p if k in founder.get('bounds',{})]
  if not keys:break
  for k in rng.sample(keys,min(len(keys),rng.choice([1,2]))):
   lo,hi=founder['bounds'][k];old=p[k]
   if not isinstance(old,(int,float)):continue
   value=max(lo,min(hi,old+rng.gauss(0,(hi-lo)*.08)))
   g['parameters'][k]=int(round(value)) if isinstance(old,int) else round(value,5)
  out.append(g)
 return out

async def run(family='wallet_convergence'):
 await init_db()
 async with connection() as c:
  available=founders()
  if family not in available:raise ValueError('unknown_founder')
  rows=await load_rows(c);fee=await measured_roundtrip_network_fee_sol(c);rate,_=sol_gbp_rate();cost=fee*rate
  await c.execute(SCHEMA)
  data_mints=len({r['mint'] for r in rows})
  previous=await c.fetchval("SELECT result FROM queen_targeted_descendant_runs WHERE family=$1 ORDER BY id DESC LIMIT 1",family)
  if isinstance(previous,str):previous=json.loads(previous)
  if previous and previous.get('data_mints')==data_mints:
   return {'family':family,'status':'unchanged_evidence_no_repeat','tested':0,'baseline_score':previous.get('baseline_score'),'best_descendant_score':previous.get('best_descendant_score'),'breeding_authorized':False}
  parts=split_rows(rows)[:2];base=available[family]
  reference=[evaluate(base,s,TARGET_STAKE_GBP,cost) for s in parts]
  candidates=[]
  for g in descendants(base):
   metrics=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in parts]
   candidates.append({'score':score(metrics),'train_n':metrics[0].get('n',0),'validation_n':metrics[1].get('n',0),'train_net_gbp':metrics[0].get('avg_net_gbp'),'validation_net_gbp':metrics[1].get('avg_net_gbp'),'genome':g})
  best=max(candidates,key=lambda x:x['score']) if candidates else None
  base_score=score(reference)
  report={'family':family,'data_mints':data_mints,'tested':len(candidates),'baseline_score':base_score,
   'best_descendant_score':best['score'] if best else None,'best_descendant':best,
   'better_than_founder':bool(best and best['score']>base_score),
   'independent_proof':False,'holdout_untouched':True,'breeding_authorized':False,
   'paper_authorized':False,'live_authorized':False}
  await c.execute(SCHEMA)
  await c.execute('INSERT INTO queen_targeted_descendant_runs(family,result) VALUES($1,$2::jsonb)',family,json.dumps(report))
 return report
if __name__=='__main__':
 import sys
 print(json.dumps(asyncio.run(run(sys.argv[1] if len(sys.argv)>1 else 'wallet_convergence')),default=str))

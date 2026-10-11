"""Independent intrahorizon stop/take research diagnostic, NEVER execution authority.
Requires observed price samples near both entry and planned exit; applies identical
roundtrip friction. Gaps and ambiguous observation order are explicit exclusions.
"""
import asyncio,json
from datetime import timedelta
from db import init_db,connection

def simulate(entry_at,entry_price,samples,hold_minutes,stop_pct=None,take_pct=None,friction_bps=30,max_gap_seconds=600):
 if not entry_price or entry_price<=0 or hold_minutes<=0:return {'status':'invalid_entry'}
 end=entry_at+timedelta(minutes=hold_minutes)
 path=sorted((t,float(p)) for t,p in samples if entry_at<=t<=end and p is not None and float(p)>0)
 if not path or (path[0][0]-entry_at).total_seconds()>max_gap_seconds:
  return {'status':'insufficient_path','reason':'missing_entry_coverage'}
 if (end-path[-1][0]).total_seconds()>max_gap_seconds:
  return {'status':'insufficient_path','reason':'missing_exit_coverage'}
 last=entry_at
 for t,_ in path:
  if (t-last).total_seconds()>max_gap_seconds:return {'status':'insufficient_path','reason':'interior_gap'}
  last=t
 exit_at,exit_price,reason=path[-1][0],path[-1][1],'time'
 for t,p in path:
  delta=(p/entry_price-1)*100
  if stop_pct is not None and delta<=stop_pct:
   exit_at,exit_price,reason=t,p,'stop';break
  if take_pct is not None and delta>=take_pct:
   exit_at,exit_price,reason=t,p,'take';break
 return {'status':'observed_path','exit_reason':reason,'exit_at':exit_at.isoformat(),
         'gross_pct':(exit_price/entry_price-1)*100,
         'net_pct':(exit_price/entry_price-1)*100-friction_bps/100,
         'friction_bps':friction_bps,'samples':len(path),
         'caveat':'sampled timestamps are not executable quotes, slippage and fill likelihood unmeasured'}

async def run(limit=300):
 await init_db();out=[]
 async with connection() as c:
  rows=await c.fetch("""SELECT e.run_id,e.candidate_id,e.genome_id,e.observed_at,e.hold_minutes,
   a.baseline,a.genome->'parameters' params,r.entry_price
   FROM family_tournament_entries e JOIN family_tournament_ants a USING(run_id,genome_id)
   JOIN research_candidates r ON r.id=e.candidate_id
   WHERE e.run_id='hive-loss-tail-1'
   ORDER BY e.candidate_id DESC,e.genome_id LIMIT $1""",limit)
  for row in rows:
   params=row['params'];params=json.loads(params) if isinstance(params,str) else params
   samples=await c.fetch("""SELECT observed_at,price FROM research_price_path
      WHERE candidate_id=$1 AND observed_at>=$2 AND observed_at<=$3 ORDER BY observed_at""",
      row['candidate_id'],row['observed_at'],row['observed_at']+timedelta(minutes=row['hold_minutes']))
   result=simulate(row['observed_at'],float(row['entry_price'] or 0),
     [(x['observed_at'],x['price']) for x in samples],row['hold_minutes'],
     params.get('stop_loss_pct'),params.get('take_profit_pct'))
   out.append({'candidate_id':row['candidate_id'],'genome_id':row['genome_id'],
     'control':row['baseline'],**result})
 return {'n':len(out),'observed':sum(x['status']=='observed_path' for x in out),
  'excluded':sum(x['status']!='observed_path' for x in out),
  'distinct_candidates':len(set(x['candidate_id'] for x in out)),
  'complete_candidates':len(set(x['candidate_id'] for x in out if x['status']=='observed_path')),
  'by_genome':{g:{'observed':sum(x['genome_id']==g and x['status']=='observed_path' for x in out),
    'stop':sum(x['genome_id']==g and x.get('exit_reason')=='stop' for x in out),
    'take':sum(x['genome_id']==g and x.get('exit_reason')=='take' for x in out)}
    for g in set(x['genome_id'] for x in out)},
  'coverage_pct':round(100*sum(x['status']=='observed_path' for x in out)/max(1,len(out)),2),
  'warning':'INSUFFICIENT INDEPENDENT PRICE PATH COVERAGE: no stop-loss qualification' if len(set(x['candidate_id'] for x in out if x['status']=='observed_path'))<30 else 'descriptive_paper_only',
  'authority':'diagnostic_only_no_promotions','sample_limit':limit}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

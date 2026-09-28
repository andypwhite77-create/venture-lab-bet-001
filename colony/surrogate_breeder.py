"""Elite-directed second-wave breeding from historical nursery results.
A lightweight surrogate: successful parameter regions bias mutation, while random exploration remains.
"""
from __future__ import annotations
import copy,json,random,statistics
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate,robust_score,select_finalists,founders,_set,SEED
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate

async def guided_family(conn,family,n=5000):
 row=await conn.fetchrow('SELECT id,finalists FROM historical_nursery_runs WHERE family=$1 ORDER BY created_at DESC LIMIT 1',family)
 if not row:return {'family':family,'status':'no_nursery'}
 fs=row['finalists'];fs=json.loads(fs) if isinstance(fs,str) else fs
 elite=[x for x in fs if float(x.get('robust_score',-999))>0 and x.get('genome')]
 if len(elite)<2:return {'family':family,'status':'insufficient_positive_elite','positive_elite':len(elite)}
 elite=elite[:30];base=founders()[family];keys=list(base['parameters']);rng=random.Random(f'guided:{SEED}:{family}')
 # learn centre/spread of successful region, then sample mostly there
 stats={}
 for k in keys:
  vals=[float(x['genome']['parameters'][k]) for x in elite]
  stats[k]=(statistics.fmean(vals),max(statistics.pstdev(vals), (base['bounds'][k][1]-base['bounds'][k][0])*.01))
 pop=[];seen=set();i=0
 while len(pop)<n:
  parent=copy.deepcopy(rng.choice(elite)['genome']); changed=rng.sample(keys,rng.choice([1,1,2]))
  for k in changed:
   mu,sd=stats[k]
   if rng.random()<.80:v=rng.gauss(mu,sd*.75)
   else:
    lo,hi=parent['bounds'][k];v=rng.uniform(lo,hi)
   _set(parent,k,v)
  parent['surrogate']={'source_nursery':row['id'],'ordinal':i,'changed':changed,'mode':'elite_directed'}
  gid=genome_id(parent)
  if gid not in seen:pop.append(parent);seen.add(gid)
  i+=1
 rows=await load_rows(conn);splits=split_rows(rows);results=[]
 fee_sol=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();fixed_gbp=fee_sol*rate
 for g in pop:
  parts=[evaluate(g,s,TARGET_STAKE_GBP,fixed_gbp) for s in splits];rs=robust_score(parts)
  results.append({'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'robust_score':rs})
 finals=select_finalists(results,100,rng_seed=f'guided:{SEED}:{family}')
 summary={'family':family,'status':'ok','tested':len(pop),'positive_elite':len(elite),'positive_finalists':sum(float(x.get('robust_score',-999))>0 for x in finals),
          'best_score':max((float(x.get('robust_score',-999)) for x in finals),default=-999),'stake_gbp':TARGET_STAKE_GBP,'fixed_cost_gbp':fixed_gbp}
 await conn.execute('''INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary)
   VALUES($1,$2,$3,$4::jsonb,$5::jsonb)''',family,len(pop),len(rows),json.dumps(finals),json.dumps({**summary,'mode':'surrogate_elite_directed'}))
 return summary

async def run_all(conn):
 out=[]
 for fam in ('reversal','momentum','order_flow','wallet_convergence'):out.append(await guided_family(conn,fam))
 return out

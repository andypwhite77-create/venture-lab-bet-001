"""Queen-led general pattern recognition with breadth/concentration pressure.
Searches arbitrary sensor predicates rather than named trading hypotheses.
Train+validation drive evolution; holdout is sealed until finalists are fixed.
"""
import copy,json,random,statistics,os,pickle,time
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
SENSORS={'price_change_m5':(-20,20),'price_change_h1':(-50,60),'volume_liquidity_m5':(.001,.8),'dex_buy_ratio_m5':(.2,.9),'buy_acceleration':(.3,7),'flow_ratio_15':(.1,8),'buy_wallets_30':(0,300),'buys_15':(0,500),'sells_15':(0,500),'buys_30':(0,800),'sells_30':(0,800),'liquidity_usd':(1000,600000),'volume_m5':(0,500000)}
HOLDS=(5,10,15,30,45,60,240)

def random_genome(rng):
 keys=rng.sample(list(SENSORS),rng.randint(2,6));p={}
 for k in keys:
  lo,hi=SENSORS[k];p[k]={rng.choice(('min','max')):rng.uniform(lo,hi)}
 return {'family':'queen_pattern','species':'general_pattern','parameters':{'hold_minutes':rng.choice(HOLDS)},'predicates':p,'bounds':{}}

def mutate(g,rng):
 x=copy.deepcopy(g);p=x['predicates']
 if rng.random()<.15 and len(p)<7:
  avail=[k for k in SENSORS if k not in p]
  if avail:
   k=rng.choice(avail);lo,hi=SENSORS[k];p[k]={rng.choice(('min','max')):rng.uniform(lo,hi)}
 if rng.random()<.10 and len(p)>2:del p[rng.choice(list(p))]
 for k,r in p.items():
  if rng.random()<.6:
   lo,hi=SENSORS[k];op=next(iter(r));r[op]=max(lo,min(hi,r[op]+rng.gauss(0,(hi-lo)*.05)))
 if rng.random()<.2:x['parameters']['hold_minutes']=rng.choice(HOLDS)
 return x

def selection_fitness(parts):
 t,v=parts[:2]
 if t.get('n',0)<15 or v.get('n',0)<10:return -999.0
 # Queen knows the game, not Spartan's hidden cutoffs: reward breadth, survival and distributed contribution.
 breadth=(min(1.0,t['n']/40.0)*min(1.0,v['n']/25.0))**0.5
 concentration=max(float(t.get('outlier',1)),float(v.get('outlier',1)))
 if concentration>.50:return -999.0
 consistency=min(float(t.get('win_rate',0)),float(v.get('win_rate',0)))
 base=.35*t['nursery_score']+.65*v['nursery_score']+.45*min(t['nursery_score'],v['nursery_score'])
 return base*breadth + .10*consistency - max(0,concentration-.30)*1.15

async def run(conn,wave_size=50000,waves=6,seed=300933,checkpoint='/data/queen_pattern_checkpoint.pkl'):
 rng=random.Random(seed);rows=await load_rows(conn);splits=split_rows(rows)
 fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
 parents=[];last=[];tested=0;start_wave=1
 if checkpoint and os.path.exists(checkpoint):
  try:
   cp=pickle.load(open(checkpoint,'rb'));parents=cp['parents'];tested=cp['tested'];start_wave=cp['wave']+1;rng.setstate(cp['rng_state'])
   print(json.dumps({'event':'queen_resumed','from_wave':start_wave,'tested':tested,'urgency':'EXTREME'}),flush=True)
  except Exception as e: print(json.dumps({'event':'checkpoint_rejected','error':str(e)}),flush=True)
 for wave in range(start_wave,waves+1):
  pop=[random_genome(rng) for _ in range(wave_size)] if not parents else [mutate(rng.choice(parents),rng) if rng.random()<.90 else random_genome(rng) for _ in range(wave_size)]
  ranked=[]
  for g in pop:
   parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits];tested+=1
   ranked.append({'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'selection_score':selection_fitness(parts),'wave':wave})
  ranked.sort(key=lambda x:x['selection_score'],reverse=True);parents=[x['genome'] for x in ranked[:300]];last=ranked
  eligible=sum(x['selection_score']>-900 for x in ranked)
  print(json.dumps({'wave':wave,'tested':tested,'eligible':eligible,'best':ranked[0]['selection_score'],'urgency':'EXTREME','directive':'breed faster; kill fragility; earn expansion'}),flush=True)
  if checkpoint:
   os.makedirs(os.path.dirname(checkpoint),exist_ok=True);pickle.dump({'wave':wave,'tested':tested,'parents':parents,'rng_state':rng.getstate(),'best':ranked[0]['selection_score'],'eligible':eligible,'saved_at':time.time()},open(checkpoint,'wb'))
 finalists=[x for x in last if x['selection_score']>-900][:40]
 summary={'mode':'queen_general_pattern_breadth','tested':tested,'waves':waves,'rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),'finalists':len(finalists),'holdout_positive':sum(x['holdout'].get('avg_net_gbp',-1)>0 for x in finalists),'holdout_not_used_for_selection':True,'min_train_events':15,'min_validation_events':10,'selection_concentration_ceiling':.50,'fresh_blood_rate':.10}
 if checkpoint and os.path.exists(checkpoint): os.remove(checkpoint)
 await conn.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES('queen_pattern',$1,$2,$3::jsonb,$4::jsonb)",tested,len(rows),json.dumps(finalists),json.dumps(summary))
 return summary,finalists

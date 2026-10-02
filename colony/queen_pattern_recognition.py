"""Queen-led general pattern recognition with breadth/concentration pressure.
Searches arbitrary sensor predicates rather than named trading hypotheses.
Train+validation drive evolution; holdout is sealed until finalists are fixed.
"""
import copy,json,random,statistics,os,pickle,time,collections
from concurrent.futures import ProcessPoolExecutor
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate,regime_name
from colony.queen_memory import load_memory
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
from colony.queen_ecology import load as load_ecology, strategy as ecology_strategy
from colony.queen_mutation_credit import load as load_mutation_credit, save as save_mutation_credit, choose as choose_mutation_operator, record as record_mutation_credit, summarise as summarise_mutation_credit
SENSORS={'price_change_m5':(-20,20),'price_change_h1':(-50,60),'volume_liquidity_m5':(.001,.8),'dex_buy_ratio_m5':(.2,.9),'buy_acceleration':(.3,7),'flow_ratio_15':(.1,8),'buy_wallets_30':(0,300),'buys_15':(0,500),'sells_15':(0,500),'buys_30':(0,800),'sells_30':(0,800),'liquidity_usd':(1000,600000),'volume_m5':(0,500000),'trend_alignment':(-1200,1800),'short_vs_hour':(-30,30),'flow_imbalance_15':(-1,1),'flow_imbalance_30':(-1,1),'flow_shift':(-2,2),'activity_30':(0,1600),'activity_h1':(0,5000),'flow_imbalance_h1':(-1,1),'buy_activity_change':(-1,12),'volume_liquidity_h1':(0,10),'fdv_liquidity_ratio':(0,1000),'marketcap_liquidity_ratio':(0,1000),'pair_age_hours':(0,10000),'advisor_reversal':(0,1),'advisor_momentum':(0,1),'advisor_order_flow':(0,1),'advisor_exhaustion':(0,1),'advisor_mean_reversion':(0,1),'advisor_count':(0,5),'live_signal_reversal':(0,1),'live_signal_exhaustion':(0,1),'live_signal_momentum':(0,1),'live_signal_order_flow':(0,1),'live_signal_wallet_convergence':(0,1),'live_signal_mean_reversion':(0,1),'live_signal_count':(0,6),'live_council_available':(0,1),'hist_context_available':(0,1),'hist_return_24h':(-100,500),'hist_return_7d':(-100,5000),'hist_volatility_24h':(0,300),'hist_volume_ratio_24h':(0,20),'hist_drawdown_7d_pct':(-100,0),'hist_position_7d':(0,1)}
HOLDS=(5,10,15,30,45,60,240)
METHODOLOGY_VERSION='queen-v8-directed-mutation-credit'
# Queen may evolve simple risk management; all decisions are fixed before sealed holdout.
STOP_LOSSES=(None,-5,-8,-12,-18,-25)
TAKE_PROFITS=(None,5,8,12,20,35,60)

_EVAL_SPLITS=None
_EVAL_COST=0.0

def _worker_init(splits,cost):
 global _EVAL_SPLITS,_EVAL_COST
 _EVAL_SPLITS=splits;_EVAL_COST=cost

def _worker_score(g):
 parts=[evaluate(g,s,TARGET_STAKE_GBP,_EVAL_COST) for s in _EVAL_SPLITS[:2]]
 return {'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'selection_score':selection_fitness(parts,g)}

def _parse_niche(sig):
 try:
  head,body=sig.split(':',1); hold=int(head[1:]); keys=[k for k in body.split(',') if k in SENSORS]
  return hold,keys
 except Exception:return None,[]

def _ecology_signature(g):
 p=g.get('predicates',{}); hold=g.get('parameters',{}).get('hold_minutes')
 return f"h{hold}:"+','.join(sorted(p))

def _sensor_pool(memory=None):
 memory=memory or {}; availability=memory.get('sensor_availability') or {}
 pool=[k for k in SENSORS if float(availability.get(k,1.0) or 0)>=.10]
 return pool or list(SENSORS)

def _sensor_range(k,memory=None):
 memory=memory or {}; r=(memory.get('sensor_ranges') or {}).get(k)
 if isinstance(r,(list,tuple)) and len(r)==2 and float(r[0])<float(r[1]): return float(r[0]),float(r[1])
 return SENSORS[k]

def random_genome(rng,memory=None,eco_plan=None,eco_state=None):
 memory=memory or {}; eco_plan=eco_plan or {'exploit':.55,'adjacent_explore':.25,'wild_scouts':.20,'top_niches':[]}
 sensor_pool=_sensor_pool(memory)
 preferred=[]
 for k in list(memory.get('prospective_preferred_features',[]))+list(memory.get('preferred_features',[])):
  if k in sensor_pool and k not in preferred: preferred.append(k)
 under=[k for k in memory.get('underexplored_features',[]) if k in sensor_pool]
 niches=[_parse_niche(x) for x in eco_plan.get('top_niches',[])]; niches=[(h,[k for k in ks if k in sensor_pool]) for h,ks in niches]; niches=[x for x in niches if x[1]]
 r=rng.random(); wild=float(eco_plan.get('wild_scouts',.20)); adjacent=float(eco_plan.get('adjacent_explore',.25))
 mode='wild' if r<wild else ('adjacent' if r<wild+adjacent else 'exploit')
 hold=None; keys=[]; n=rng.randint(1,4)
 if mode in ('exploit','adjacent') and niches:
  hold,base=rng.choice(niches); keys=rng.sample(base,min(len(base),n))
  if mode=='adjacent':
   if under and rng.random()<.75:
    k=rng.choice(under)
    if k not in keys:
     if len(keys)>=n: keys[rng.randrange(len(keys))]=k
     else: keys.append(k)
   elif keys and rng.random()<.65:
    keys[rng.randrange(len(keys))]=rng.choice([k for k in sensor_pool if k not in keys] or keys)
 if not keys and mode!='wild' and preferred and rng.random()<.85:
  keys=rng.sample(preferred,min(len(preferred),rng.randint(1,min(n,len(preferred)))))
 pool=[k for k in sensor_pool if k not in keys]
 if len(keys)<n: keys += rng.sample(pool,min(len(pool),n-len(keys)))
 keys=keys[:n]; p={}
 for k in keys:
  lo,hi=_sensor_range(k,memory);p[k]={rng.choice(('min','max')):rng.uniform(lo,hi)}
 g={'family':'queen_pattern','species':'general_pattern_'+mode,'parameters':{'hold_minutes':hold if hold in HOLDS else rng.choice(HOLDS),'stop_loss_pct':rng.choice(STOP_LOSSES),'take_profit_pct':rng.choice(TAKE_PROFITS)},'predicates':p,'bounds':{}}
 # Graveyard is a soft avoidance signal, never a permanent ban.
 grave=(eco_state or {}).get('graveyard',{})
 if _ecology_signature(g) in grave and rng.random()<.80:
  g['parameters']['hold_minutes']=rng.choice(HOLDS)
  if _ecology_signature(g) in grave and g['predicates']:
   old=rng.choice(list(g['predicates'])); del g['predicates'][old]
   avail=[k for k in sensor_pool if k not in g['predicates']]
   if avail:
    k=rng.choice(avail);lo,hi=_sensor_range(k,memory);g['predicates'][k]={rng.choice(('min','max')):rng.uniform(lo,hi)}
 return g

def _behaviour_key(x):
 g=x['genome']; prm=g.get('parameters',{})
 return (x['train'].get('event_signature'),x['validation'].get('event_signature'),int(prm.get('hold_minutes',15)),prm.get('stop_loss_pct'),prm.get('take_profit_pct'))

MUTATION_MODES={
 'local':{'add':.02,'delete':.12,'touch':.55,'sigma':.025,'hold':.08,'risk':.05},
 'standard':{'add':.05,'delete':.30,'touch':.60,'sigma':.05,'hold':.20,'risk':.12},
 'wide':{'add':.12,'delete':.35,'touch':.82,'sigma':.12,'hold':.35,'risk':.22},
}

def mutate(g,rng,allowed_sensors=None,sensor_ranges=None,operator='standard'):
 x=copy.deepcopy(g);p=x['predicates']; allowed=list(allowed_sensors or SENSORS); sensor_ranges=sensor_ranges or {}
 cfg=MUTATION_MODES.get(operator,MUTATION_MODES['standard'])
 def rr(k):
  r=sensor_ranges.get(k); return (float(r[0]),float(r[1])) if isinstance(r,(list,tuple)) and len(r)==2 and float(r[0])<float(r[1]) else SENSORS[k]
 if rng.random()<cfg['add'] and len(p)<5:
  avail=[k for k in allowed if k not in p]
  if avail:
   k=rng.choice(avail);lo,hi=rr(k);p[k]={rng.choice(('min','max')):rng.uniform(lo,hi)}
 if rng.random()<cfg['delete'] and len(p)>1:del p[rng.choice(list(p))]
 for k,r in p.items():
  if rng.random()<cfg['touch']:
   lo,hi=rr(k);op=next(iter(r));r[op]=max(lo,min(hi,r[op]+rng.gauss(0,(hi-lo)*cfg['sigma'])))
 if rng.random()<cfg['hold']:x['parameters']['hold_minutes']=rng.choice(HOLDS)
 if rng.random()<cfg['risk']:x['parameters']['stop_loss_pct']=rng.choice(STOP_LOSSES)
 if rng.random()<cfg['risk']:x['parameters']['take_profit_pct']=rng.choice(TAKE_PROFITS)
 return x

def selection_fitness(parts,genome=None):
 t,v=parts[:2]
 # Anti-loophole breadth floor: viable strategies must work across a meaningful
 # number of independent assets in both breeding-visible partitions.
 if t.get('n',0)<18 or v.get('n',0)<12:return -999.0
 # Hard economic gate: consistency may reward profitable robustness, but can never
 # rescue a strategy that loses money on either breeding-visible partition.
 if float(t.get('avg_net_gbp',-1e9))<=0 or float(v.get('avg_net_gbp',-1e9))<=0:return -999.0
 # Queen knows the game, not Spartan's hidden cutoffs: reward breadth, survival and distributed contribution.
 breadth=(min(1.0,t['n']/90.0)*min(1.0,v['n']/45.0))**0.5
 # Keep rewarding safety margin well beyond the viability floor; do not let evolution camp on it.
 breadth_margin=(min(1.0,t['n']/140.0)*min(1.0,v['n']/70.0))**0.5
 breadth_pressure=breadth**1.35
 coverage=min(1.0,(v['n']/max(1,t['n']))/.55)
 concentration=max(float(t.get('outlier',1)),float(v.get('outlier',1)))
 if concentration>.50:return -999.0
 consistency=min(float(t.get('win_rate',0)),float(v.get('win_rate',0)))
 base=.35*t['nursery_score']+.65*v['nursery_score']+.45*min(t['nursery_score'],v['nursery_score'])
 # Soft fragility pressure: very young or thin-liquidity concentration is allowed only
 # when the economic edge is strong enough to pay for the extra risk.
 low_age=max(float(t.get('low_age_fraction',0)),float(v.get('low_age_fraction',0)))
 low_liq=max(float(t.get('low_liquidity_fraction',0)),float(v.get('low_liquidity_fraction',0)))
 fragility_penalty=.12*max(0,low_age-.35)+.10*max(0,low_liq-.35)
 # Parsimony pressure prevents increasingly specific predicate stacks from winning
 # merely by shrinking the opportunity set around a few historical winners.
 predicate_n=len((genome or {}).get('predicates',{}))
 complexity_penalty=.06*max(0,predicate_n-2)
 return base*breadth_pressure*(.45+.55*coverage) + .22*breadth_margin + .12*consistency - max(0,concentration-.28)*1.25 - fragility_penalty - complexity_penalty

def select_finalists_breadth(ranked):
 # Breeding-visible handoff only. Cap actual executed behaviour, not cosmetic genotype variation.
 eligible=[x for x in ranked if x['selection_score']>-900]
 picked=[]; counts={}
 for x in eligible[:1000]:
  sig=_behaviour_key(x)
  if counts.get(sig,0)>=1: continue
  counts[sig]=counts.get(sig,0)+1; picked.append(x)
  if len(picked)>=100: break
 return picked

async def _load_swarm_plan(conn):
 try:
  r=await conn.fetchrow("""SELECT observed_at,briefing FROM swarm_queen_journal
    WHERE briefing->'research_plan'->>'authority'='research_allocation_only'
      AND briefing->'research_plan'->>'source'='research_safe_swarm_ecology'
    ORDER BY id DESC LIMIT 1""")
  if not r:return None
  if time.time()-r['observed_at'].timestamp()>3600:return None
  b=r['briefing']; b=json.loads(b) if isinstance(b,str) else dict(b or {})
  p=dict(b.get('research_plan') or {})
  if p.get('authority')!='research_allocation_only' or p.get('source')!='research_safe_swarm_ecology':return None
  w=float(p.get('wild_scouts',.2)); a=float(p.get('adjacent_explore',.25)); e=float(p.get('exploit',.55))
  if not (.15<=w<=.50 and .15<=a<=.50 and .10<=e<=.65):return None
  total=w+a+e
  if not (.98<=total<=1.02):return None
  return {'wild_scouts':w/total,'adjacent_explore':a/total,'exploit':e/total,
          'focus_sensors':[x for x in (p.get('focus_sensors') or []) if x in SENSORS][:8],
          'avoid_niches':list(p.get('avoid_niches') or [])[:8],
          'observed_at':r['observed_at'].isoformat(),'source':'swarm_queen'}
 except Exception:
  return None

def _freeze_exam_rows(rows):
 frozen=[]
 for r in rows:
  frozen.append({'mint':r['mint'],'flat':r.get('flat',{}),'returns':{str(k):float(v) for k,v in r.get('returns',{}).items()}})
 payload=json.dumps(frozen,sort_keys=True,separators=(',',':'),default=str)
 import hashlib
 return frozen,hashlib.sha256(payload.encode()).hexdigest()

async def run(conn,wave_size=50000,waves=6,seed=300933,checkpoint='/data/queen_pattern_checkpoint.pkl'):
 rng=random.Random(seed);memory=load_memory();eco_state=load_ecology();eco_plan=ecology_strategy(eco_state)
 swarm_plan=await _load_swarm_plan(conn)
 if swarm_plan:
  eco_plan.update({k:swarm_plan[k] for k in ('exploit','adjacent_explore','wild_scouts')})
  focus=[k for k in swarm_plan.get('focus_sensors',[]) if k in SENSORS]
  memory['underexplored_features']=focus+[k for k in memory.get('underexplored_features',[]) if k not in focus]
  memory['preferred_features']=focus+[k for k in memory.get('preferred_features',[]) if k not in focus]
  grave=eco_state.setdefault('graveyard',{})
  for sig in swarm_plan.get('avoid_niches',[]):grave.setdefault(sig,{'reason':'swarm_queen_soft_avoidance','revisitable':True})
 rows=await load_rows(conn)
 if swarm_plan:
  print(json.dumps({'event':'swarm_guidance_applied','plan':{k:swarm_plan.get(k) for k in ('exploit','adjacent_explore','wild_scouts','focus_sensors','avoid_niches','source')}}),flush=True)
 fresh_rate=max(.20,min(.50,float(eco_plan.get('wild_scouts',.20))))
 # Prospective career evidence may guide breeding. Mints whose outcomes taught Queen
 # are allowed in TRAINING (training is allowed to know them), but are permanently
 # barred from validation and sealed holdout. This preserves independent exams without
 # throwing away most of the information-rich training population.
 exp_mints=set(memory.get('prospective_experience_mints',[]))
 rows=sorted(rows,key=lambda r:r['created_at'])
 first={}
 for r in rows:first.setdefault(r['mint'],r['created_at'])
 clean=sorted((m for m in first if m not in exp_mints),key=lambda m:first[m])
 n=len(clean); a=int(n*.60); b=int(n*.80)
 train_mints=set(clean[:a])|set(exp_mints); val_mints=set(clean[a:b]); hold_mints=set(clean[b:])
 splits=([r for r in rows if r['mint'] in train_mints],
         [r for r in rows if r['mint'] in val_mints],
         [r for r in rows if r['mint'] in hold_mints])
 selection_rows=splits[0]+splits[1]
 sensor_availability={k:sum(1 for r in selection_rows if k in r.get('flat',{}) and r['flat'].get(k) is not None)/max(1,len(selection_rows)) for k in SENSORS}
 memory['sensor_availability']=sensor_availability
 sensor_ranges={}
 for k in SENSORS:
  vals=[]
  for r in selection_rows:
   v=r.get('flat',{}).get(k)
   if v is None: continue
   try: vals.append(float(v))
   except (TypeError,ValueError): pass
  if len(vals)>=20:
   vals.sort(); lo=vals[max(0,int(.05*(len(vals)-1)))]; hi=vals[min(len(vals)-1,int(.95*(len(vals)-1)))]
   if lo<hi: sensor_ranges[k]=[lo,hi]
 memory['sensor_ranges']=sensor_ranges
 active_sensors=_sensor_pool(memory)
 # Do not spend compute on focus sensors that are almost never observable in breeding-visible data.
 memory['underexplored_features']=[k for k in memory.get('underexplored_features',[]) if k in active_sensors]
 memory['preferred_features']=[k for k in memory.get('preferred_features',[]) if k in active_sensors]
 fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
 parents=[];last=[];tested=0;start_wave=1;mutation_credit=load_mutation_credit()
 if checkpoint and os.path.exists(checkpoint):
  try:
   cp=pickle.load(open(checkpoint,'rb'))
   if cp.get('methodology_version')!=METHODOLOGY_VERSION: raise ValueError('checkpoint_methodology_mismatch')
   parents=cp['parents'];tested=cp['tested'];start_wave=cp['wave']+1;rng.setstate(cp['rng_state']);fresh_rate=float(cp.get('fresh_rate',fresh_rate))
   print(json.dumps({'event':'queen_resumed','from_wave':start_wave,'tested':tested,'urgency':'EXTREME','methodology_version':METHODOLOGY_VERSION}),flush=True)
  except Exception as e: print(json.dumps({'event':'checkpoint_rejected','error':str(e)}),flush=True)
 for wave in range(start_wave,waves+1):
  provenance=[]
  if not parents:
   templates=[x.get('genome') for x in memory.get('prospective_parent_templates',[]) if isinstance(x.get('genome'),dict)]
   pop=[random_genome(rng,memory,eco_plan,eco_state) for _ in range(wave_size)]; provenance=[None]*len(pop)
   # Dedicated gene-seed injection: add a separate 40k descendant cohort without
   # replacing wild exploration. This preserves creativity while exploiting robust careers.
   gene_seed_n=int(os.getenv('QUEEN_GENE_SEED_N','40000')) if templates else 0
   for _ in range(gene_seed_n):
    base=copy.deepcopy(rng.choice(templates));base['family']='queen_pattern';base['species']='career_descendant';pop.append(mutate(base,rng,active_sensors,sensor_ranges));provenance.append(None)
  else:
   pop=[];provenance=[]
   for _ in range(wave_size):
    if rng.random()<(1.0-fresh_rate):
     parent=rng.choice(parents); op=choose_mutation_operator(rng,mutation_credit)
     child=mutate(parent['genome'],rng,active_sensors,sensor_ranges,operator=op)
     pop.append(child);provenance.append((op,float(parent['selection_score']),parent['genome_id']))
    else:
     pop.append(random_genome(rng,memory,eco_plan,eco_state));provenance.append(None)
  # Breeding never evaluates sealed holdout. Score train+validation only, in parallel.
  workers=max(1,min(int(os.getenv('QUEEN_EVAL_WORKERS','2')),os.cpu_count() or 1))
  if workers==1:
   ranked=[]
   for g in pop:
    parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits[:2]]
    ranked.append({'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'selection_score':selection_fitness(parts,g),'wave':wave})
  else:
   with ProcessPoolExecutor(max_workers=workers,initializer=_worker_init,initargs=(splits,cost)) as ex:
    ranked=list(ex.map(_worker_score,pop,chunksize=128))
   for x in ranked:x['wave']=wave
  tested+=len(pop)
  if any(provenance):
   for x,prov in zip(ranked,provenance):
    if prov:
     op,parent_score,_=prov; mutation_credit=record_mutation_credit(op,parent_score,x['selection_score'],mutation_credit)
   save_mutation_credit(mutation_credit)
  mutation_summary=summarise_mutation_credit(mutation_credit)
  ranked.sort(key=lambda x:x['selection_score'],reverse=True)
  # Preserve actual behavioural diversity: identical executed opportunity sets + risk
  # controls may contribute only a few parents, regardless of cosmetic genome differences.
  parents=[]; phenos={}
  for x in ranked:
   if x['selection_score']<=-900: continue
   sig=_behaviour_key(x)
   if phenos.get(sig,0)>=3: continue
   phenos[sig]=phenos.get(sig,0)+1;parents.append({'genome_id':x['genome_id'],'genome':x['genome'],'selection_score':x['selection_score']})
   if len(parents)>=300: break
  behaviour_groups=len(phenos)
  base_fresh=max(.20,min(.50,float(eco_plan.get('wild_scouts',.20))))
  fresh_rate=max(base_fresh,.50 if behaviour_groups<10 else (.40 if behaviour_groups<20 else (.30 if behaviour_groups<40 else base_fresh)))
  last=ranked
  eligible=sum(x['selection_score']>-900 for x in ranked)
  print(json.dumps({'wave':wave,'tested':tested,'eligible':eligible,'best':ranked[0]['selection_score'],'parent_behaviour_groups':behaviour_groups,'fresh_blood_rate':fresh_rate,'urgency':'EXTREME','directive':'breed faster; kill fragility; earn expansion','mutation_credit':mutation_summary}),flush=True)
  if checkpoint:
   os.makedirs(os.path.dirname(checkpoint),exist_ok=True);pickle.dump({'methodology_version':METHODOLOGY_VERSION,'wave':wave,'tested':tested,'parents':parents,'rng_state':rng.getstate(),'best':ranked[0]['selection_score'],'eligible':eligible,'fresh_rate':fresh_rate,'saved_at':time.time()},open(checkpoint,'wb'))
 # Only after breeding is completely finished do we open holdout for the fixed top pool.
 diagnostic_pool=[x for x in last if x['selection_score']>-900][:500]
 for x in diagnostic_pool:
  x['holdout']=evaluate(x['genome'],splits[2],TARGET_STAKE_GBP,cost)
 finalists=select_finalists_breadth(last)
 finalist_by_id={x['genome_id']:x for x in diagnostic_pool}
 for x in finalists:
  if 'holdout' not in x:
   x['holdout']=evaluate(x['genome'],splits[2],TARGET_STAKE_GBP,cost)
 # Diagnostic only: inspect holdout by validation rank after breeding is complete.
 # This is never fed back into selection, memory, mutation, or Spartan thresholds.
 bands=[]
 for lo,hi in ((1,40),(41,100),(101,200),(201,300),(301,500)):
  xs=diagnostic_pool[lo-1:hi]
  vals=[float(x['holdout'].get('avg_net_gbp',0) or 0) for x in xs]
  bands.append({'rank_lo':lo,'rank_hi':min(hi,len(diagnostic_pool)),'n':len(xs),
                'holdout_positive':sum(v>0 for v in vals),
                'holdout_mean_gbp':statistics.fmean(vals) if vals else None,
                'holdout_median_gbp':statistics.median(vals) if vals else None,
                'holdout_best_gbp':max(vals) if vals else None})
 positives=[(i+1,float(x['holdout'].get('avg_net_gbp',0) or 0),x['genome_id']) for i,x in enumerate(diagnostic_pool) if float(x['holdout'].get('avg_net_gbp',0) or 0)>0]
 diag={'generated_at':time.time(),'pool_n':len(diagnostic_pool),'bands':bands,
       'positive_total':len(positives),'first_positive_rank':positives[0][0] if positives else None,
       'best_positive':max(positives,key=lambda z:z[1]) if positives else None}
 try:
  with open('/data/queen_rank_diagnostic.json','w') as f: json.dump(diag,f,indent=2)
 except Exception as e:
  print(json.dumps({'event':'queen_rank_diagnostic_write_failed','error':type(e).__name__}),flush=True)
 print(json.dumps({'event':'queen_rank_diagnostic',**diag}),flush=True)
 exam_rows,exam_hash=_freeze_exam_rows(splits[2])
 # Research-safe regime coverage telemetry: train+validation only, after finalists are frozen.
 breeding_rows=splits[0]+splits[1]; regime_coverage={}
 for reg in ('selloff','surge','high_activity','chop'):
  rr=[r for r in breeding_rows if regime_name(r)==reg]
  vals=[]; supported=0
  for x in finalists:
   m=evaluate(x['genome'],rr,TARGET_STAKE_GBP,cost)
   if m.get('n',0)>=5:
    supported+=1
    if m.get('avg_net_gbp') is not None: vals.append(float(m['avg_net_gbp']))
  regime_coverage[reg]={'rows':len(rr),'mints':len({r['mint'] for r in rr}),'supported_finalists':supported,
                        'positive_finalists':sum(v>0 for v in vals),'median_avg_net_gbp':statistics.median(vals) if vals else None}
 weak_counts=collections.Counter(_ecology_signature(x['genome']) for x in last if x.get('selection_score',-999)<=-900)
 weak_niches=[{'signature':sig,'count':cnt} for sig,cnt in weak_counts.most_common(20) if cnt>=5]
 summary={'mode':'queen_general_pattern_breadth','tested':tested,'waves':waves,'rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),'finalists':len(finalists),'holdout_positive':sum(x['holdout'].get('avg_net_gbp',-1)>0 for x in finalists),'holdout_not_used_for_selection':True,'finalist_handoff':'behaviour_capped_from_top1000','historical_holdout_used_for_algorithm_design':True,'prospective_proof_required':True,'min_train_events':18,'min_validation_events':12,'breeding_diversity_cap_per_behaviour':3,'validation_coverage_reward':True,'selection_concentration_ceiling':.50,'fresh_blood_rate':fresh_rate,'memory_campaigns':memory.get('campaigns',0),'memory_preferred_features':memory.get('preferred_features',[]),'prospective_preferred_features':memory.get('prospective_preferred_features',[]),'prospective_parent_templates':len(memory.get('prospective_parent_templates',[])),'prospective_mints_forced_train':len(exp_mints),'active_ant_genomes_frozen':True,'experience_breeds_descendants':True,'gene_seed_extra_first_wave':int(os.getenv('QUEEN_GENE_SEED_N','40000')) if memory.get('prospective_parent_templates') else 0,'ecology_plan':eco_plan,'swarm_research_plan':swarm_plan,'behavioral_parent_cap':3,'behavioral_finalist_cap':1,'methodology_version':METHODOLOGY_VERSION,'exam_snapshot_version':2,'exam_snapshot_sha256':exam_hash,'exam_holdout_rows':exam_rows,'sensor_availability':{k:round(v,4) for k,v in sensor_availability.items()},'active_sensor_count':len(active_sensors),'empirical_sensor_range_count':len(sensor_ranges),'breeding_regime_coverage':regime_coverage,'weak_niches':weak_niches,'mutation_credit':summarise_mutation_credit(mutation_credit)}
 if checkpoint and os.path.exists(checkpoint): os.remove(checkpoint)
 await conn.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES('queen_pattern',$1,$2,$3::jsonb,$4::jsonb)",tested,len(rows),json.dumps(finalists,default=str),json.dumps(summary,default=str))
 return summary,finalists

"""Queen-led phenotype discovery.
The Queen evolves both which sensors matter and their predicates; no fixed named strategy required.
Research only: selection uses train+validation, holdout is sealed until finalists are chosen.
"""
import json,random,copy
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
SENSORS={
 'price_change_m5':(-15,15),'price_change_h1':(-50,50),'dex_buy_ratio_m5':(.25,.9),
 'volume_liquidity_m5':(.001,.8),'buy_acceleration':(.5,6),'flow_ratio_15':(.2,7),
 'wallet_convergence':(0,1),'liquidity_usd':(1000,500000),'age_minutes':(1,1440)}

def random_genome(rng):
    keys=rng.sample(list(SENSORS),rng.randint(2,5));pred={}
    for k in keys:
        lo,hi=SENSORS[k];v=rng.uniform(lo,hi);pred[k]={rng.choice(['min','max']):v}
    return {'family':'queen_discovery','species':'queen_invented','parameters':{'hold_minutes':rng.choice([5,10,15,30,45,60])},'predicates':pred,'bounds':{}}
def mutate(g,rng):
    x=copy.deepcopy(g);p=x['predicates']
    if rng.random()<.12 and len(p)<6:
        k=rng.choice([k for k in SENSORS if k not in p]);lo,hi=SENSORS[k];p[k]={rng.choice(['min','max']):rng.uniform(lo,hi)}
    if rng.random()<.08 and len(p)>2:del p[rng.choice(list(p))]
    for k,r in p.items():
        if rng.random()<.55:
            lo,hi=SENSORS[k];key=next(iter(r));r[key]=max(lo,min(hi,r[key]+rng.gauss(0,(hi-lo)*.06)))
        if rng.random()<.03:
            old=next(iter(r));v=r.pop(old);r['max' if old=='min' else 'min']=v
    if rng.random()<.2:x['parameters']['hold_minutes']=rng.choice([5,10,15,30,45,60])
    return x

def fitness(parts):
    t,v=parts[:2]
    if t.get('n',0)<8 or v.get('n',0)<6:return -999
    a=t.get('nursery_score',-999);b=v.get('nursery_score',-999)
    return min(a,b)+.25*(a+b)
async def run(conn,wave_size=25000,waves=4,seed=300926):
    rng=random.Random(seed);rows=await load_rows(conn);splits=split_rows(rows)
    fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
    parents=[];tested=0;last=[]
    for wave in range(1,waves+1):
        pop=[random_genome(rng) for _ in range(wave_size)] if not parents else [mutate(rng.choice(parents),rng) if rng.random()<.9 else random_genome(rng) for _ in range(wave_size)]
        ranked=[]
        for g in pop:
            parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits];tested+=1
            ranked.append({'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'selection_score':fitness(parts),'wave':wave})
        ranked.sort(key=lambda x:x['selection_score'],reverse=True);parents=[x['genome'] for x in ranked[:100]];last=ranked
        print(json.dumps({'wave':wave,'tested':tested,'viable':sum(x['selection_score']>-900 for x in ranked),'best':ranked[0]['selection_score']}),flush=True)
    finalists=[x for x in last if x['selection_score']>-900][:20]
    summary={'mode':'queen_open_discovery','tested':tested,'waves':waves,'rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),'finalists':len(finalists),'holdout_positive':sum(x['holdout'].get('avg_net_gbp',-1)>0 for x in finalists),'holdout_not_used_for_selection':True,'fresh_blood_rate':.10}
    await conn.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES('queen_discovery',$1,$2,$3::jsonb,$4::jsonb)",tested,len(rows),json.dumps(finalists),json.dumps(summary))
    return summary,finalists

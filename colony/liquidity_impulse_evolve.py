"""Liquidity impulse / participation expansion discovery bloodline.
Replaces failed early-momentum family with a less directional hypothesis:
activity expansion + adequate liquidity + balanced-to-positive participation before extension.
Selection is train+validation only; holdout remains sealed until finalist selection.
"""
import copy,json,random
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate,robust_score,select_finalists
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
FAMILY='liquidity_impulse'

def make_genome(rng):
 return {'family':FAMILY,'species':'participation_expansion','parameters':{'hold_minutes':rng.choice([5,10,15,30,45])},'predicates':{
  'volume_liquidity_m5':{'min':rng.uniform(.01,.35)},'liquidity_usd':{'min':rng.uniform(10000,300000)},
  'dex_buy_ratio_m5':{'min':rng.uniform(.48,.68)},'price_change_m5':{'min':rng.uniform(-4,1),'max':rng.uniform(2,12)},
  'price_change_h1':{'max':rng.uniform(8,40)}},'bounds':{}}
def mutate(g,rng):
 x=copy.deepcopy(g);p=x['predicates']; cfg={'volume_liquidity_m5':(.04,.001,.8),'liquidity_usd':(35000,1000,500000),'dex_buy_ratio_m5':(.04,.3,.9),'price_change_h1':(4,-10,60)}
 for k,(sd,lo,hi) in cfg.items():
  key=next(iter(p[k]));p[k][key]=max(lo,min(hi,p[k][key]+rng.gauss(0,sd)))
 for key,sd,lo,hi in [('min',1,-8,6),('max',1.5,1,25)]:p['price_change_m5'][key]=max(lo,min(hi,p['price_change_m5'][key]+rng.gauss(0,sd)))
 if p['price_change_m5']['max']<=p['price_change_m5']['min']:p['price_change_m5']['max']=p['price_change_m5']['min']+2
 if rng.random()<.25:x['parameters']['hold_minutes']=rng.choice([5,10,15,30,45])
 return x
async def run(conn,n=30000,seed=300930):
 rng=random.Random(seed);rows=await load_rows(conn);splits=split_rows(rows);fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
 def test(g):
  parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits]
  return {'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'robust_score':robust_score(parts)}
 scored=[test(make_genome(rng)) for _ in range(n//2)];parents=sorted(scored,key=lambda x:x['robust_score'],reverse=True)[:100]
 for _ in range(n-len(scored)):scored.append(test(mutate(rng.choice(parents)['genome'],rng)))
 finals=select_finalists(scored,10,rng_seed=FAMILY)
 summary={'mode':'liquidity_impulse_first_evolve','replaces':'momentum','tested':len(scored),'rows':len(rows),'selection_positive':sum(x['robust_score']>0 for x in scored),'finalists':len(finals),'holdout_positive':sum(x['holdout'].get('avg_net_gbp',-1)>0 for x in finals),'holdout_not_used_for_selection':True}
 await conn.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES($1,$2,$3,$4::jsonb,$5::jsonb)",FAMILY,len(scored),len(rows),json.dumps(finals),json.dumps(summary));return summary,finals

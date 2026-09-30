"""Overshoot recovery bloodline replacing failed breakout-failure/order-flow search.
Tests violent short-horizon dislocation with surviving liquidity and participation, rather than breakout continuation/failure.
Research only; holdout is sealed until finalist selection.
"""
import copy,json,random
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate,robust_score,select_finalists
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
FAMILY='overshoot_recovery'
def make_genome(rng):
 return {'family':FAMILY,'species':'overshoot_recovery','parameters':{'hold_minutes':rng.choice([5,10,15,30,45,60])},'predicates':{
  'price_change_m5':{'max':rng.uniform(-10,-1)},'price_change_h1':{'min':rng.uniform(-30,-2)},
  'dex_buy_ratio_m5':{'min':rng.uniform(.35,.65)},'volume_liquidity_m5':{'min':rng.uniform(.003,.25)},'liquidity_usd':{'min':rng.uniform(10000,300000)}},'bounds':{}}
def mutate(g,rng):
 x=copy.deepcopy(g);p=x['predicates'];cfg={'price_change_m5':(2,-25,1),'price_change_h1':(5,-50,10),'dex_buy_ratio_m5':(.05,.2,.85),'volume_liquidity_m5':(.035,.001,.8),'liquidity_usd':(35000,1000,500000)}
 for k,(sd,lo,hi) in cfg.items():
  key=next(iter(p[k]));p[k][key]=max(lo,min(hi,p[k][key]+rng.gauss(0,sd)))
 if rng.random()<.25:x['parameters']['hold_minutes']=rng.choice([5,10,15,30,45,60])
 return x
async def run(conn,n=30000,seed=300931):
 rng=random.Random(seed);rows=await load_rows(conn);splits=split_rows(rows);fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
 def test(g):
  parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits]
  return {'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'robust_score':robust_score(parts)}
 scored=[test(make_genome(rng)) for _ in range(n//2)];parents=sorted(scored,key=lambda x:x['robust_score'],reverse=True)[:100]
 for _ in range(n-len(scored)):scored.append(test(mutate(rng.choice(parents)['genome'],rng)))
 finals=select_finalists(scored,10,rng_seed=FAMILY)
 summary={'mode':'overshoot_recovery_first_evolve','replaces':'order_flow','tested':len(scored),'rows':len(rows),'selection_positive':sum(x['robust_score']>0 for x in scored),'finalists':len(finals),'holdout_positive':sum(x['holdout'].get('avg_net_gbp',-1)>0 for x in finals),'holdout_not_used_for_selection':True}
 await conn.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES($1,$2,$3,$4::jsonb,$5::jsonb)",FAMILY,len(scored),len(rows),json.dumps(finals),json.dumps(summary));return summary,finals

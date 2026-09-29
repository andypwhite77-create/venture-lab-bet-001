"""Discovery evolution for Breakout Failure.
Hypothesis: an extended move attempts continuation, then short-term price/flow fail.
Research only; holdout is never used for selection.
"""
import copy,json,random
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
FAMILY='order_flow'

def make_genome(rng):
    return {'family':FAMILY,'species':'breakout_failure','parameters':{'hold_minutes':rng.choice([5,10,15,30])},'predicates':{
      'price_change_h1':{'min':rng.uniform(6,35)},'price_change_m5':{'min':rng.uniform(-10,-1),'max':rng.uniform(-.8,2)},
      'dex_buy_ratio_m5':{'max':rng.uniform(.40,.62)},'flow_ratio_15':{'max':rng.uniform(.25,1.1)},
      'volume_liquidity_m5':{'min':rng.uniform(.003,.20)}},'bounds':{}}

def mutate(g,rng):
    x=copy.deepcopy(g);p=x['predicates']
    p['price_change_h1']['min']+=rng.gauss(0,4);p['price_change_m5']['min']+=rng.gauss(0,1.5);p['price_change_m5']['max']+=rng.gauss(0,1)
    p['dex_buy_ratio_m5']['max']+=rng.gauss(0,.035);p['flow_ratio_15']['max']+=rng.gauss(0,.12);p['volume_liquidity_m5']['min']+=rng.gauss(0,.025)
    p['price_change_h1']['min']=max(2,min(50,p['price_change_h1']['min']));p['price_change_m5']['min']=max(-20,min(1,p['price_change_m5']['min']))
    p['price_change_m5']['max']=max(-5,min(5,p['price_change_m5']['max']));p['dex_buy_ratio_m5']['max']=max(.3,min(.75,p['dex_buy_ratio_m5']['max']))
    p['flow_ratio_15']['max']=max(.1,min(2,p['flow_ratio_15']['max']));p['volume_liquidity_m5']['min']=max(.001,min(.6,p['volume_liquidity_m5']['min']))
    if p['price_change_m5']['max']<=p['price_change_m5']['min']:p['price_change_m5']['max']=p['price_change_m5']['min']+1
    if rng.random()<.25:x['parameters']['hold_minutes']=rng.choice([5,10,15,30])
    return x
async def run(conn,n=50000,seed=300926):
    rng=random.Random(seed);rows=await load_rows(conn);splits=split_rows(rows)
    fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
    def test(g):
      parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits]
      s0=parts[0].get('nursery_score',-999.0);s1=parts[1].get('nursery_score',-999.0);sel=min(s0,s1)+.25*(s0+s1)
      return {'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'selection_score':sel}
    scored=[test(make_genome(rng)) for _ in range(n//2)]
    parents=sorted(scored,key=lambda x:x['selection_score'],reverse=True)[:100]
    for _ in range(n-len(scored)):scored.append(test(mutate(rng.choice(parents)['genome'],rng)))
    eligible=[x for x in scored if x['train']['n']>=7 and x['validation']['n']>=7]
    finalists=sorted(eligible,key=lambda x:x['selection_score'],reverse=True)[:10]
    summary={'mode':'breakout_failure_first_evolve','tested':len(scored),'rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),
      'eligible':len(eligible),'positive_train_validation':sum(x['train']['avg_net_gbp']>0 and x['validation']['avg_net_gbp']>0 for x in eligible),
      'finalists':len(finalists),'holdout_positive':sum(x['holdout']['avg_net_gbp']>0 for x in finalists),'holdout_not_used_for_selection':True}
    await conn.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES('order_flow',$1,$2,$3::jsonb,$4::jsonb)",len(scored),len(rows),json.dumps(finalists),json.dumps(summary))
    return summary,finalists

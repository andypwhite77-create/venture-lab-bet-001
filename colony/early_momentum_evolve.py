"""Discovery evolution for Early Momentum / Acceleration.
Seek moves being born, not already-extended price strength. Paper research only.
"""
import copy,json,random
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate,robust_score,select_finalists
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
FAMILY='momentum'

def make_genome(rng):
    return {'family':FAMILY,'species':'early_acceleration','parameters':{'hold_minutes':rng.choice([5,10,15,30])},'predicates':{
      'buy_acceleration':{'min':rng.uniform(1.05,4.0)},'flow_ratio_15':{'min':rng.uniform(1.05,4.5)},
      'dex_buy_ratio_m5':{'min':rng.uniform(.52,.78)},'volume_liquidity_m5':{'min':rng.uniform(.005,.25)},
      'price_change_m5':{'min':rng.uniform(-2,3),'max':rng.uniform(3.5,12)},
      'price_change_h1':{'max':rng.uniform(8,35)}},'bounds':{}}

def mutate(g,rng):
    x=copy.deepcopy(g);p=x['predicates']
    for k,scale in [('buy_acceleration',.3),('flow_ratio_15',.35),('dex_buy_ratio_m5',.035),('volume_liquidity_m5',.025)]:
      p[k]['min']+=rng.gauss(0,scale)
    p['price_change_m5']['min']+=rng.gauss(0,1);p['price_change_m5']['max']+=rng.gauss(0,1.5);p['price_change_h1']['max']+=rng.gauss(0,3)
    p['buy_acceleration']['min']=max(.8,min(6,p['buy_acceleration']['min']));p['flow_ratio_15']['min']=max(.8,min(7,p['flow_ratio_15']['min']))
    p['dex_buy_ratio_m5']['min']=max(.45,min(.9,p['dex_buy_ratio_m5']['min']));p['volume_liquidity_m5']['min']=max(.001,min(.6,p['volume_liquidity_m5']['min']))
    p['price_change_m5']['min']=max(-5,min(6,p['price_change_m5']['min']));p['price_change_m5']['max']=max(2,min(20,p['price_change_m5']['max']));p['price_change_h1']['max']=max(5,min(50,p['price_change_h1']['max']))
    if p['price_change_m5']['max']<=p['price_change_m5']['min']:p['price_change_m5']['max']=p['price_change_m5']['min']+2
    if rng.random()<.25:x['parameters']['hold_minutes']=rng.choice([5,10,15,30])
    return x
async def run(conn,n=50000,seed=290926):
    rng=random.Random(seed);rows=await load_rows(conn);splits=split_rows(rows)
    fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
    def test(g):
      parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits]
      # Selection fitness deliberately excludes holdout.
      sel=min(parts[0]['nursery_score'],parts[1]['nursery_score'])+.25*(parts[0]['nursery_score']+parts[1]['nursery_score'])
      return {'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'selection_score':sel,'robust_score':robust_score(parts)}
    initial=[test(make_genome(rng)) for _ in range(n//2)]
    parents=sorted(initial,key=lambda x:x['selection_score'],reverse=True)[:100]
    scored=initial[:]
    for _ in range(n-len(initial)):scored.append(test(mutate(rng.choice(parents)['genome'],rng)))
    # choose solely on train+validation, then reveal holdout in saved finalists
    eligible=[x for x in scored if x['train']['n']>=7 and x['validation']['n']>=7]
    finalists=sorted(eligible,key=lambda x:x['selection_score'],reverse=True)[:10]
    summary={'mode':'early_momentum_first_evolve','tested':len(scored),'rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),
      'eligible':len(eligible),'positive_train_validation':sum(x['train']['avg_net_gbp']>0 and x['validation']['avg_net_gbp']>0 for x in eligible),
      'finalists':len(finalists),'holdout_positive':sum(x['holdout']['avg_net_gbp']>0 for x in finalists),'holdout_not_used_for_selection':True}
    await conn.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES('momentum',$1,$2,$3::jsonb,$4::jsonb)",len(scored),len(rows),json.dumps(finalists),json.dumps(summary))
    return summary,finalists

"""Independent mean-reversion bloodline replacing dead wallet convergence.
Hypothesis: sharp short-term displacement inside a non-collapsing liquid market tends to partially revert.
Selection uses train+validation only; holdout remains sealed until finalists are chosen.
Research/paper only; never grants live-money authority.
"""
import copy,json,random
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate,robust_score,select_finalists
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate

def make_genome(rng):
    return {'family':'mean_reversion','species':'displacement_reversion','parameters':{'hold_minutes':rng.choice([5,10,15,30,45,60])},
      'predicates':{'price_change_m5':{'max':rng.uniform(-4,-.4)},
                    'price_change_h1':{'max':rng.uniform(-2,15)},
                    'liquidity_usd':{'min':rng.uniform(15000,300000)},
                    'dex_buy_ratio_m5':{'min':rng.uniform(.30,.62)}},'bounds':{}}

def mutate(g,rng):
    x=copy.deepcopy(g); scales={'price_change_m5':1.2,'price_change_h1':3.0,'liquidity_usd':30000,'dex_buy_ratio_m5':.04}
    limits={'price_change_m5':(-15,2),'price_change_h1':(-15,30),'liquidity_usd':(1000,500000),'dex_buy_ratio_m5':(.2,.8)}
    for k,rule in x['predicates'].items():
        if rng.random()<.75:
            key=next(iter(rule));lo,hi=limits[k];rule[key]=max(lo,min(hi,float(rule[key])+rng.gauss(0,scales[k])))
    if rng.random()<.25:x['parameters']['hold_minutes']=rng.choice([5,10,15,30,45,60])
    return x

async def run(conn,n=50000,seed=300927):
    rng=random.Random(seed);rows=await load_rows(conn);splits=split_rows(rows)
    fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
    def test(g):
        parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits]
        return {'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'robust_score':robust_score(parts)}
    scored=[test(make_genome(rng)) for _ in range(n//2)]
    parents=sorted(scored,key=lambda x:x['robust_score'],reverse=True)[:100]
    for _ in range(n-len(scored)):scored.append(test(mutate(rng.choice(parents)['genome'],rng)))
    finals=select_finalists(scored,10,rng_seed='mean-reversion')
    summary={'mode':'mean_reversion_first_evolve','replaces':'wallet_convergence','tested':len(scored),'rows':len(rows),
      'unique_mints':len({r['mint'] for r in rows}),'selection_positive':sum(x['robust_score']>0 for x in scored),
      'finalists':len(finals),'holdout_positive':sum(x['holdout'].get('avg_net_gbp',-1)>0 for x in finals),
      'best_selection_score':max((x['robust_score'] for x in scored),default=-999),'holdout_not_used_for_selection':True}
    await conn.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES('mean_reversion',$1,$2,$3::jsonb,$4::jsonb)",len(scored),len(rows),json.dumps(finals),json.dumps(summary))
    return summary,finals

"""Historical discovery experiment for an Exhaustion species.
Looks for an extended move whose short-term move/flow is no longer confirming it.
Discovery only; never grants live authority.
"""
import copy,json,random
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate,robust_score,select_finalists
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate

def make_genome(rng):
    # Current data cannot express second derivatives directly, so use h1-vs-m5 divergence
    # plus weakening buy participation as a first exhaustion hypothesis.
    h1=rng.uniform(6,35); m5=rng.uniform(-8,4); br=rng.uniform(.45,.72); vl=rng.uniform(.005,.30)
    return {'family':'exhaustion','parameters':{'hold_minutes':rng.choice([5,10,15,30,45,60])},
      'predicates':{'price_change_h1':{'min':h1},'price_change_m5':{'max':m5},
                    'dex_buy_ratio_m5':{'max':br},'volume_liquidity_m5':{'min':vl}},
      'bounds':{}}

def mutate(g,rng):
    x=copy.deepcopy(g)
    for k,rule in x['predicates'].items():
        key='min' if 'min' in rule else 'max'; v=float(rule[key]); scale={'price_change_h1':4,'price_change_m5':2,'dex_buy_ratio_m5':.04,'volume_liquidity_m5':.03}[k]
        rule[key]=v+rng.gauss(0,scale)
    x['predicates']['price_change_h1']['min']=max(2,min(50,x['predicates']['price_change_h1']['min']))
    x['predicates']['price_change_m5']['max']=max(-15,min(8,x['predicates']['price_change_m5']['max']))
    x['predicates']['dex_buy_ratio_m5']['max']=max(.35,min(.85,x['predicates']['dex_buy_ratio_m5']['max']))
    x['predicates']['volume_liquidity_m5']['min']=max(.001,min(.8,x['predicates']['volume_liquidity_m5']['min']))
    if rng.random()<.25:x['parameters']['hold_minutes']=rng.choice([5,10,15,30,45,60])
    return x
async def run(conn,n=50000,seed=290926):
    rng=random.Random(seed);rows=await load_rows(conn);splits=split_rows(rows)
    fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
    pop=[make_genome(rng) for _ in range(n//2)]; scored=[]
    def test(g):
        parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits]
        return {'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'robust_score':robust_score(parts)}
    scored=[test(g) for g in pop]; parents=sorted(scored,key=lambda x:x['robust_score'],reverse=True)[:100]
    # Second half evolves against train+validation only. Holdout remains untouched.
    for _ in range(n-len(pop)):
        g=mutate(rng.choice(parents)['genome'],rng);scored.append(test(g))
    finals=select_finalists(scored,10,rng_seed='exhaustion')
    summary={'mode':'exhaustion_first_evolve','tested':len(scored),'rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),
      'selection_positive':sum(x['robust_score']>0 for x in scored),'finalists':len(finals),'holdout_positive':sum(x['holdout'].get('avg_net_gbp',-1)>0 for x in finals),
      'best_selection_score':max((x['robust_score'] for x in scored),default=-999),'note':'first hypothesis; holdout not used for selection'}
    await conn.execute('''INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary)
      VALUES('exhaustion',$1,$2,$3::jsonb,$4::jsonb)''',len(scored),len(rows),json.dumps(finals),json.dumps(summary))
    return summary,finals

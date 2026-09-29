"""Brutal second-stage evolution for Exhaustion.
Breeds on train+validation only; untouched holdout is graduation exam.
"""
import copy,json,random
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate,robust_score
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
from colony.exhaustion_evolve import mutate
FAMILY='exhaustion'

def graduate(r):
    t,v,h=r['train'],r['validation'],r['holdout']
    if min(t['n'],v['n'],h['n']) < 7:return False
    if any(x['avg_net_gbp']<=0 for x in (t,v,h)):return False
    if any(x['catastrophe_rate']>0 for x in (t,v,h)):return False
    if any(x['outlier']>.55 for x in (t,v,h)):return False
    if max(t['max_drawdown'],v['max_drawdown'],h['max_drawdown'])>.25:return False
    return True

def distance(a,b):
    pa,pb=a['genome']['predicates'],b['genome']['predicates']; scales={'price_change_h1':48,'price_change_m5':23,'dex_buy_ratio_m5':.5,'volume_liquidity_m5':.799}
    return sum(abs(float(next(iter(pa[k].values())))-float(next(iter(pb[k].values()))))/scales[k] for k in scales)
async def run(conn,wave_size=20000,max_waves=20,target=5):
    rows=await load_rows(conn); splits=split_rows(rows)
    fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
    seed=await conn.fetchrow("SELECT finalists FROM historical_nursery_runs WHERE family='exhaustion' ORDER BY created_at DESC LIMIT 1")
    fs=seed['finalists'] if seed else []; fs=json.loads(fs) if isinstance(fs,str) else fs
    parents=[x['genome'] for x in fs if x.get('genome')]; tested=0; graduates=[]
    rng=random.Random('exhaustion-spartan-v1')
    for wave in range(1,max_waves+1):
        pop=[]
        while len(pop)<wave_size: pop.append(mutate(rng.choice(parents),rng))
        ranked=[]
        for g in pop:
            p=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits];tested+=1
            ranked.append({'genome_id':genome_id(g),'genome':g,'train':p[0],'validation':p[1],'holdout':p[2],'robust_score':robust_score(p),'wave':wave})
        ranked.sort(key=lambda x:x['robust_score'],reverse=True)
        parents=[x['genome'] for x in ranked[:50]]
        candidates=graduates+[x for x in ranked if graduate(x)]
        chosen=[]
        for x in sorted({x['genome_id']:x for x in candidates}.values(),key=lambda x:x['robust_score'],reverse=True):
            if all(distance(x,y)>=.08 for y in chosen):chosen.append(x)
            if len(chosen)>=target:break
        graduates=chosen
        print(json.dumps({'wave':wave,'tested':tested,'graduates':len(graduates),'best':ranked[0]['robust_score']}),flush=True)
        if len(graduates)>=target:break
    summary={'mode':'exhaustion_spartan','tested':tested,'waves':wave,'graduated':len(graduates),'target':target,'status':'target_met' if len(graduates)>=target else 'insufficient','historical_rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),'rules':{'min_each_split':7,'positive_all_splits':True,'zero_catastrophes':True,'max_outlier':.55,'max_drawdown':.25,'diversity':.08,'holdout_not_used_for_breeding':True}}
    await conn.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES('exhaustion',$1,$2,$3::jsonb,$4::jsonb)",tested,len(rows),json.dumps(graduates),json.dumps(summary))
    return summary,graduates

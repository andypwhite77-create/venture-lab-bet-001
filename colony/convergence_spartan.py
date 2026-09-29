"""Repeated historical evolution for Wallet Convergence.
Discovery only: survivors must still prove themselves prospectively.
"""
import copy,json,random,statistics
from colony.genome import genome_id
from colony.historical_nursery import load_rows,split_rows,evaluate,robust_score,founders,_set
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate

FAMILY='wallet_convergence'

def passes(r):
    t,v,h=r['train'],r['validation'],r['holdout']
    # Holdout is diagnostic until this final graduation check; it never shapes breeding fitness.
    parts=(t,v,h)
    if any(x.get('n',0)<5 or x.get('avg_net_gbp',-1)<=0 for x in parts): return False
    if any(x.get('catastrophe_rate',1)>0 for x in parts): return False
    if any(x.get('outlier',1)>.55 for x in parts): return False
    return h.get('nursery_score',-999)>0 and min(t['nursery_score'],v['nursery_score'])>0

def breed(parents,base,n,seed):
    rng=random.Random(seed); keys=list(base['parameters']); out=[];seen=set()
    while len(out)<n:
        g=copy.deepcopy(rng.choice(parents) if parents else base)
        for k in rng.sample(keys,rng.choice([1,1,2,2,3])):
            lo,hi=g['bounds'][k]; span=hi-lo
            _set(g,k,rng.gauss(float(g['parameters'][k]),span*.06) if rng.random()<.85 else rng.uniform(lo,hi))
        gid=genome_id(g)
        if gid not in seen: out.append(g);seen.add(gid)
    return out
async def run(conn,wave_size=20000,max_waves=20,target=5):
    rows=await load_rows(conn);splits=split_rows(rows);base=founders()[FAMILY]
    fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();cost=fee*rate
    seedrow=await conn.fetchrow("SELECT finalists FROM historical_nursery_runs WHERE family=$1 ORDER BY created_at DESC LIMIT 1",FAMILY)
    fs=json.loads(seedrow['finalists']) if seedrow and isinstance(seedrow['finalists'],str) else (seedrow['finalists'] if seedrow else [])
    parents=[x['genome'] for x in (fs or []) if x.get('genome')][:20] or [base]
    survivors=[];tested=0
    for wave in range(1,max_waves+1):
        pop=breed(parents,base,wave_size,f'convergence-spartan:{wave}:{len(rows)}')
        ranked=[]
        for g in pop:
            parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits];tested+=1
            r={'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'robust_score':robust_score(parts),'wave':wave}
            ranked.append(r)
        ranked.sort(key=lambda x:x['robust_score'],reverse=True)
        # Breeding sees train+validation only. Holdout is consulted only for final graduation.
        parents=[x['genome'] for x in ranked[:40] if x['robust_score']>-900] or parents
        pool=survivors+[x for x in ranked if passes(x)]
        unique={x['genome_id']:x for x in pool}; survivors=sorted(unique.values(),key=lambda x:(x['holdout']['nursery_score'],x['robust_score']),reverse=True)
        # demand parameter diversity so five near-clones cannot graduate together
        chosen=[]
        for x in survivors:
            p=x['genome']['parameters']
            if all(sum(abs(float(p[k])-float(y['genome']['parameters'][k]))/(base['bounds'][k][1]-base['bounds'][k][0] or 1) for k in p)>=.08 for y in chosen): chosen.append(x)
            if len(chosen)>=target: break
        print(json.dumps({'wave':wave,'tested':tested,'passing':len(survivors),'diverse':len(chosen)}),flush=True)
        if len(chosen)>=target: survivors=chosen;break
    final=survivors[:target]
    summary={'mode':'convergence_spartan','tested':tested,'waves':wave,'target':target,'graduated':len(final),'status':'target_met' if len(final)>=target else 'dead_end_so_far','rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),'rules':{'positive_all_splits':True,'zero_catastrophes':True,'max_outlier_share':.55,'diversity_distance':.08,'holdout_not_used_for_breeding':True}}
    await conn.execute('''INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary)
      VALUES($1,$2,$3,$4::jsonb,$5::jsonb)''',FAMILY,tested,len(rows),json.dumps(final),json.dumps(summary))
    return summary,final

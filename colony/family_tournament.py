"""Parallel 100-ant evolutionary tournaments for non-Reversal bloodlines.
Shadow/prospective only; no live execution authority.
"""
from __future__ import annotations
import copy, json, math, random, statistics
from pathlib import Path
from colony.forward import eligible
from colony.genome import genome_id
from colony.selection import ant_metrics
from colony.paper_economics import TARGET_STAKE_GBP,adjusted_return_pct,measured_roundtrip_network_fee_sol,sol_gbp_rate

ROOT=Path(__file__).resolve().parent
DEFAULT_SEED=28092026
STAGES=[(100,20,60),(60,35,30),(30,40,15),(15,50,5),(5,25,5)]
FAMILIES=("momentum","order_flow","wallet_convergence")

def founder(family):
    founders=json.load(open(ROOT/'control-founders.json'))
    return copy.deepcopy(next(g for g in founders if g['family']==family))

def _set(g,key,val):
    lo,hi=g['bounds'][key]; old=g['parameters'][key]
    val=max(lo,min(hi,val)); g['parameters'][key]=int(round(val)) if isinstance(old,int) else round(float(val),6)

def _mutate_key(g,key,rng):
    old=g['parameters'][key]; lo,hi=g['bounds'][key]
    if key=='cooldown_minutes' and float(old)==0:
        val=rng.choice([0,3,5,8,10,15,20,30,45,60])
    else:
        span=float(hi)-float(lo); val=float(old)+rng.gauss(0,.12*span)
    _set(g,key,val)
    if g['parameters'][key]==old:
        step=1 if isinstance(old,int) else max((hi-lo)*.01,.001)
        _set(g,key,float(old)+(step if rng.random()<.5 else -step))

def make_population(family,size=100,seed=DEFAULT_SEED):
    base=founder(family); keys=list(base['parameters']); cohorts=keys+['mixed']
    rng=random.Random(f'{seed}:{family}'); out=[base]; seen={genome_id(base)}; i=0
    while len(out)<size:
        cohort=cohorts[i%len(cohorts)]; g=copy.deepcopy(base)
        changed=rng.sample(keys,2) if cohort=='mixed' else [cohort]
        for k in changed:_mutate_key(g,k,rng)
        g['tournament']={'family':family,'cohort':cohort,'ordinal':i,'seed':seed,'changed':changed}
        gid=genome_id(g)
        if gid not in seen:out.append(g);seen.add(gid)
        i+=1
        if i>size*200:raise RuntimeError('could not create unique population')
    return out

def _outlier(vals):
    pos=[x for x in vals if x>0]
    return 1.0 if not pos or sum(pos)==0 else max(pos)/sum(pos)

def score_record(returns,baseline_map,stake_gbp=TARGET_STAKE_GBP,fixed_cost_gbp=0.0):
    raw_first={}
    for mint,ret in returns:raw_first.setdefault(mint,float(ret))
    first={m:adjusted_return_pct(r,stake_gbp,fixed_cost_gbp) for m,r in raw_first.items()}
    vals=list(first.values()); m=ant_metrics(list(first.items()))
    base_adj={m:adjusted_return_pct(r,stake_gbp,fixed_cost_gbp) for m,r in baseline_map.items()}
    shared=[(r,base_adj[mint]) for mint,r in first.items() if mint in base_adj]
    edge=statistics.fmean(r-b for r,b in shared) if shared else 0.0
    tail=abs(min(0.0,min(vals))) if vals else 100.0; outlier=_outlier(vals)
    score=float(m.get('fitness',-999))+edge/100-tail/200-max(0.0,outlier-.45)
    avg_net_gbp=(statistics.fmean(vals)*stake_gbp/100.0) if vals else None
    positive_raw=[r for r in raw_first.values() if r>0]
    mean_positive=statistics.fmean(positive_raw) if positive_raw else 0.0
    break_even=(fixed_cost_gbp/(mean_positive/100.0)) if fixed_cost_gbp>0 and mean_positive>0 else (0.0 if mean_positive>0 else None)
    return {**m,'baseline_edge_pct':edge,'baseline_overlap_n':len(shared),'worst_return_pct':min(vals) if vals else None,
            'outlier_dependence':outlier,'tournament_score':score,'mints':set(first),'paper_stake_gbp':stake_gbp,
            'fixed_cost_gbp':fixed_cost_gbp,'avg_net_gbp':avg_net_gbp,'break_even_stake_gbp':break_even}

def catastrophic(r):return r.get('n',0)>=8 and r.get('catastrophe_rate',0)>=.20

def can_reproduce(r,min_n,baseline_n=0):
    comparison_ok = baseline_n < 5 or r.get('baseline_overlap_n',0) >= min(5,min_n)
    return r.get('n',0)>=min_n and not catastrophic(r) and comparison_ok

def rank_records(records):
    ranked=sorted(records.items(),key=lambda kv:kv[1]['tournament_score'],reverse=True); out=[]
    for gid,rec in ranked:
        penalty=0.0
        for _,strong in out[:20]:
            a,b=rec['mints'],strong['mints']; j=len(a&b)/max(1,len(a|b))
            if j>.90:penalty=max(penalty,(j-.90)*2)
        rr=dict(rec);rr['correlation_penalty']=penalty;rr['adjusted_score']=rr['tournament_score']-penalty;out.append((gid,rr))
    return sorted(out,key=lambda kv:kv[1]['adjusted_score'],reverse=True)

async def metrics(conn,run_id,since=None):
    clause=' AND e.observed_at >= $2' if since else ''; args=[run_id]+([since] if since else [])
    rows=await conn.fetch(f'''SELECT e.genome_id,e.mint,o.net_return_pct FROM family_tournament_entries e
      JOIN research_outcomes o ON o.candidate_id=e.candidate_id WHERE e.run_id=$1 {clause}
      AND o.horizon_minutes=(SELECT horizon_minutes FROM research_outcomes WHERE candidate_id=e.candidate_id
        ORDER BY abs(horizon_minutes-e.hold_minutes),horizon_minutes LIMIT 1)
      ORDER BY e.genome_id,e.observed_at''',*args)
    grouped={}
    for r in rows:grouped.setdefault(r['genome_id'],[]).append((r['mint'],float(r['net_return_pct'])))
    base=await conn.fetchval('SELECT genome_id FROM family_tournament_ants WHERE run_id=$1 AND baseline=true',run_id)
    bm={}
    for mint,ret in grouped.get(base,[]):bm.setdefault(mint,ret)
    fee_sol=await measured_roundtrip_network_fee_sol(conn); rate,_=sol_gbp_rate(); fixed_gbp=fee_sol*rate
    return {gid:score_record(vals,bm,TARGET_STAKE_GBP,fixed_gbp) for gid,vals in grouped.items()}

async def process_all(conn):
    runs=await conn.fetch("SELECT * FROM family_tournament_runs WHERE status='collecting' ORDER BY created_at")
    out=[]
    for run in runs:
        ants=await conn.fetch('SELECT genome_id,genome FROM family_tournament_ants WHERE run_id=$1 AND active=true',run['run_id'])
        rows=await conn.fetch('SELECT id,created_at,mint,features,market FROM research_candidates WHERE created_at >= $1 AND id>$2 ORDER BY id',run['created_at'],run['last_candidate_id'])
        ins=0
        for row in rows:
            rr=dict(row)
            for ant in ants:
                g=ant['genome']; g=json.loads(g) if isinstance(g,str) else g; gid=ant['genome_id']
                prev=await conn.fetchval('SELECT max(observed_at) FROM family_tournament_entries WHERE run_id=$1 AND genome_id=$2 AND mint=$3',run['run_id'],gid,rr['mint'])
                if not eligible(g,rr,prev):continue
                hold=int(g.get('parameters',{}).get('hold_minutes',15))
                res=await conn.execute('''INSERT INTO family_tournament_entries(run_id,genome_id,mint,candidate_id,observed_at,hold_minutes,stage_index)
                   VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING''',run['run_id'],gid,rr['mint'],rr['id'],rr['created_at'],hold,run['stage_index'])
                ins+=int(res.endswith('1'))
        if rows:await conn.execute('UPDATE family_tournament_runs SET last_candidate_id=$2 WHERE run_id=$1',run['run_id'],rows[-1]['id'])
        out.append({'run':run['run_id'],'family':run['family'],'active_ants':len(ants),'candidates':len(rows),'inserted':ins})
    return out

async def maybe_cull_all(conn):
    runs=await conn.fetch("SELECT * FROM family_tournament_runs WHERE status='collecting' ORDER BY created_at")
    results=[]
    for run in runs:
        idx=int(run['stage_index']); stage,min_n,target=STAGES[min(idx,len(STAGES)-1)]
        active=await conn.fetch('SELECT genome_id,baseline,cohort FROM family_tournament_ants WHERE run_id=$1 AND active=true',run['run_id'])
        recs=await metrics(conn,run['run_id'],run['stage_started_at'] if stage==5 else None)
        base=next((a['genome_id'] for a in active if a['baseline']),None)
        qualified=[a for a in active if recs.get(a['genome_id'],{}).get('n',0)>=min_n]
        required=len(active) if stage==5 else max(2,math.ceil(len(active)*.80))
        if len(qualified)<required:
            results.append({'family':run['family'],'stage':stage,'active':len(active),'qualified':len(qualified),'minimum_n':min_n,'culled':0});continue
        if stage==5:
            await conn.execute("UPDATE family_tournament_runs SET status='holdout_complete' WHERE run_id=$1",run['run_id'])
            results.append({'family':run['family'],'stage':5,'holdout_complete':True});continue
        ranked=rank_records({a['genome_id']:recs[a['genome_id']] for a in active if a['genome_id'] in recs})
        baseline_n=recs.get(base,{}).get('n',0) if base else 0
        keep=[base] if base else []; represented=set(); cohorts={a['genome_id']:a['cohort'] for a in active}
        for gid,r in ranked:
            if gid==base or not can_reproduce(r,min_n,baseline_n):continue
            c=cohorts.get(gid,'mixed')
            if c not in represented and len(keep)<target:keep.append(gid);represented.add(c)
        for gid,r in ranked:
            if len(keep)>=target:break
            if gid not in keep and can_reproduce(r,min_n,baseline_n):keep.append(gid)
        losers=[a['genome_id'] for a in active if a['genome_id'] not in set(keep[:target])]
        if losers:await conn.execute("UPDATE family_tournament_ants SET active=false,eliminated_at=now(),eliminated_stage=$3,elimination_reason='stage_cull' WHERE run_id=$1 AND genome_id=ANY($2::text[])",run['run_id'],losers,idx)
        await conn.execute('UPDATE family_tournament_runs SET stage_size=$2,stage_index=stage_index+1,stage_started_at=now() WHERE run_id=$1',run['run_id'],target)
        results.append({'family':run['family'],'from':stage,'to':target,'culled':len(losers)})
    return results

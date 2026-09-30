"""Run Spartan v2 against historical finalists without changing their genomes."""
import json,statistics
from colony.evaluator import matches
from colony.historical_nursery import load_rows,split_rows
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
from colony.spartan_v2 import stress_returns,behavioural_distance

def observations(genome,rows):
    hold=int(genome.get('parameters',{}).get('hold_minutes',15)); out=[]; seen=set()
    for r in rows:
        if r['mint'] in seen or not matches(genome,r['flat']): continue
        ret=r['returns'].get(hold)
        if ret is None and r['returns']:
            h=min(r['returns'],key=lambda x:abs(x-hold));ret=r['returns'][h]
        if ret is not None: out.append((r['mint'],r['mint'],float(ret)/100.0));seen.add(r['mint'])
    return out

def concentration(rs):
    pos=[x for x in rs if x>0]
    return 1.0 if not pos else max(pos)/max(sum(pos),1e-12)
async def audit_family(conn,family='exhaustion',min_events=25):
    rows=await load_rows(conn);splits=split_rows(rows)
    rec=await conn.fetchrow("SELECT finalists FROM historical_nursery_runs WHERE family=$1 AND jsonb_array_length(finalists)>0 ORDER BY created_at DESC LIMIT 1",family)
    fs=rec['finalists'];fs=json.loads(fs) if isinstance(fs,str) else fs
    fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();fixed=fee*rate; base=fixed/TARGET_STAKE_GBP
    results=[]
    for x in fs:
        g=x['genome']; obs=observations(g,splits[2]); rs=[r for _,_,r in obs]
        stress=stress_returns(rs,base,500,seed='v2:'+x['genome_id'])
        results.append({'genome_id':x['genome_id'],'events':[i for i,_,_ in obs],'n':len(rs),'mean_raw':statistics.fmean(rs) if rs else None,
          'winner_concentration':concentration(rs),'stress':stress.__dict__,'stress_pass':bool(len(rs)>=min_events and stress.mean_net>0 and stress.p05_net>0 and stress.cvar_10>0 and stress.survival_rate>=.95 and concentration(rs)<=.55)})
    # Collapse genetically different ants that execute the same opportunity set.
    behavioural_groups={}
    for a in results: behavioural_groups.setdefault(tuple(a['events']),[]).append(a['genome_id'])
    for a in results:
        a['behavioural_group_size']=len(behavioural_groups[tuple(a['events'])])
        a['behavioural_representative']=a['genome_id']==behavioural_groups[tuple(a['events'])][0]
        a['qualification_pass']=bool(a['stress_pass'] and a['behavioural_representative'])
    for i,a in enumerate(results):
        a['min_behavioural_distance']=min((behavioural_distance(a['events'],b['events']) for j,b in enumerate(results) if i!=j),default=1.0)
    return {'family':family,'base_friction_return':base,'rows':len(rows),'min_independent_events':min_events,'behavioural_groups':len(behavioural_groups),'qualified_unique_behaviours':sum(x['qualification_pass'] for x in results),'results':results}

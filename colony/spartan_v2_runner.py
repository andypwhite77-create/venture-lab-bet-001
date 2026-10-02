"""Run Spartan v2 against historical finalists without changing their genomes."""
import json,statistics,hashlib
from colony.evaluator import matches
from colony.historical_nursery import load_rows,split_rows,sampled_path_return_pct,raw_exact_return_pct
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
from colony.spartan_v2 import stress_returns,behavioural_distance,opportunity_efficiency,qualifies

def _ret_pct(genome,row,apply_risk=True):
    return sampled_path_return_pct(genome,row['returns']) if apply_risk else raw_exact_return_pct(genome,row['returns'])

def observations(genome,rows):
    out=[]; seen=set()
    for r in rows:
        if r['mint'] in seen or not matches(genome,r['flat']): continue
        ret=_ret_pct(genome,r)
        if ret is not None: out.append((r['mint'],r['mint'],ret/100.0));seen.add(r['mint'])
    return out

def opportunity_universe(genome,rows):
    out={}; seen=set()
    for r in rows:
        if r['mint'] in seen:continue
        seen.add(r['mint']); ret=_ret_pct(genome,r,apply_risk=False)
        if ret is not None:out[r['mint']]=ret/100.0
    return out

def _snapshot_rows(summary):
    raw=(summary or {}).get('exam_holdout_rows') or []
    out=[]
    for r in raw:
        out.append({'mint':r['mint'],'flat':dict(r.get('flat') or {}),
                    'returns':{int(k):float(v) for k,v in (r.get('returns') or {}).items()}})
    return out

def concentration(rs):
    pos=[x for x in rs if x>0]
    return 1.0 if not pos else max(pos)/max(sum(pos),1e-12)
async def audit_family(conn,family='exhaustion',min_events=25):
    rec=await conn.fetchrow("SELECT finalists,summary FROM historical_nursery_runs WHERE family=$1 AND jsonb_array_length(finalists)>0 ORDER BY created_at DESC LIMIT 1",family)
    fs=rec['finalists'];fs=json.loads(fs) if isinstance(fs,str) else fs
    summary=rec['summary'];summary=json.loads(summary) if isinstance(summary,str) else dict(summary or {})
    holdout=_snapshot_rows(summary)
    if not holdout:
        rows=await load_rows(conn); holdout=split_rows(rows)[2]
    fee=await measured_roundtrip_network_fee_sol(conn);rate,_=sol_gbp_rate();fixed=fee*rate; base=fixed/TARGET_STAKE_GBP
    results=[]
    for x in fs:
        g=x['genome']; obs=observations(g,holdout); rs=[r for _,_,r in obs]
        taken={i for i,_,_ in obs}; universe=opportunity_universe(g,holdout)
        rejected=[r for m,r in universe.items() if m not in taken]
        stress=stress_returns(rs,base,500,seed='v2:'+x['genome_id'])
        expectancy=statistics.fmean(rs) if rs else -1.0; opp_eff=opportunity_efficiency(rs,rejected); conc=concentration(rs)
        evidence_sufficient=bool(len(rs)>=min_events)
        passed=bool(evidence_sufficient and qualifies(stress,expectancy,opp_eff,conc))
        prm=g.get('parameters',{})
        results.append({'genome_id':x['genome_id'],'events':[i for i,_,_ in obs],'n':len(rs),'mean_raw':expectancy if rs else None,
          'hold_minutes':int(prm.get('hold_minutes',15)),'stop_loss_pct':prm.get('stop_loss_pct'),'take_profit_pct':prm.get('take_profit_pct'),
          'opportunity_efficiency':opp_eff,'winner_concentration':conc,'evidence_sufficient':evidence_sufficient,'stress':stress.__dict__,'stress_pass':passed})
    # Collapse genetically different ants that execute the same opportunity set.
    behavioural_groups={}
    def bkey(a): return (tuple(a['events']),a['hold_minutes'],a.get('stop_loss_pct'),a.get('take_profit_pct'))
    for a in results: behavioural_groups.setdefault(bkey(a),[]).append(a['genome_id'])
    for a in results:
        a['behavioural_group_size']=len(behavioural_groups[bkey(a)])
        a['behavioural_representative']=a['genome_id']==behavioural_groups[bkey(a)][0]
        a['behaviour_id']=hashlib.sha1(repr(bkey(a)).encode()).hexdigest()[:16]
        a['qualification_pass']=bool(a['stress_pass'] and a['behavioural_representative'])
    for i,a in enumerate(results):
        a['min_behavioural_distance']=min((behavioural_distance(a['events'],b['events']) for j,b in enumerate(results) if i!=j),default=1.0)
    evaluable=sum(1 for x in results if x.get('evidence_sufficient') and x.get('behavioural_representative'))
    return {'family':family,'base_friction_return':base,'rows':len(holdout),'exam_snapshot_sha256':summary.get('exam_snapshot_sha256'),'min_independent_events':min_events,'behavioural_groups':len(behavioural_groups),'evaluable_unique_behaviours':evaluable,'insufficient_evidence_unique_behaviours':max(0,len(behavioural_groups)-evaluable),'qualified_unique_behaviours':sum(x['qualification_pass'] for x in results),'results':results}

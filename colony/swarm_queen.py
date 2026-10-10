"""Swarm Queen: cross-market research director.

Today she supervises SOL research only. She monitors evidence, diagnoses regimes and blind
spots, and supplies bounded research priorities to Breeding Queen. She never spawns,
mutates or promotes genomes and never trades. When a second market is activated she is
intended to coordinate dedicated market experts rather than become every expert herself.
"""
import json, os, time, httpx, collections, math
from db import connection
from colony.queen_roles import SWARM_QUEEN, BREEDING_QUEEN, ROLE_VERSION

MODEL=os.getenv('SWARM_QUEEN_MODEL','qwen3:1.7b')
OLLAMA=os.getenv('OLLAMA_URL','http://127.0.0.1:11434/api/generate')
FAMILIES=('reversal','exhaustion','momentum','order_flow')

async def ensure_schema(c):
    await c.execute('''CREATE TABLE IF NOT EXISTS swarm_queen_journal(
      id BIGSERIAL PRIMARY KEY, observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      model TEXT NOT NULL, status TEXT NOT NULL, briefing JSONB NOT NULL,
      input_snapshot JSONB NOT NULL)''')

def _read_json(path, default=None):
    try:
        with open(path) as f:return json.load(f)
    except Exception:
        return {} if default is None else default

def _reference_baseline_snapshot(finalists, experiment="eve_reference"):
    """Research-safe reference landmarks. Never include Spartan or post-freeze proof here."""
    ants=[]; robust_sensors=collections.Counter()
    for x in finalists or []:
        g=x.get('genome',{}); prm=g.get('parameters',{}); folds=list(x.get('folds') or [])
        fold_n=[m.get('n') for m in folds]; fold_net=[m.get('avg_net_gbp') if m.get('avg_net_gbp') is not None else m.get('avg_net_return_pct') for m in folds]
        positive=bool(folds) and all(v is not None and float(v)>0 for v in fold_net)
        sensors=sorted((g.get('predicates') or {}).keys())
        if positive and g.get('species')!='control_buy_all':
            for k in sensors:robust_sensors[k]+=1
        ants.append({'species':g.get('species'),'genome_id':x.get('genome_id'),'coverage_class':x.get('coverage_class'),
                     'sensors':sensors,'hold_minutes':prm.get('hold_minutes'),'fold_n':fold_n,
                     'fold_avg_net_gbp':fold_net,'all_folds_positive':positive})
    return {'experiment':experiment,'ants':ants,
            'positive_all_folds':sum(1 for a in ants if a.get('all_folds_positive')),
            'robust_reference_sensors':[k for k,_ in robust_sensors.most_common()],
            'note':'frozen missingness-safe walk-forward landmarks only; no Spartan or prospective answers included'}


def _queen_research_snapshot(finalists, summary, previous_finalists=None):
    groups=collections.Counter(); holds=collections.Counter(); risks=collections.Counter(); sensors=collections.Counter(); combos=collections.Counter(); signatures=set()
    for x in finalists or []:
        g=x.get('genome',{}); prm=g.get('parameters',{})
        key=(x.get('train',{}).get('event_signature'),x.get('validation',{}).get('event_signature'),
             int(prm.get('hold_minutes',15)),prm.get('stop_loss_pct'),prm.get('take_profit_pct'))
        rkey=repr(key); groups[rkey]+=1; signatures.add(rkey); holds[str(prm.get('hold_minutes'))]+=1
        risks[f"{prm.get('stop_loss_pct')}|{prm.get('take_profit_pct')}"]+=1
        combo=','.join(sorted(g.get('predicates',{}))); combos[combo]+=1
        for k in g.get('predicates',{}):sensors[k]+=1
    mem=_read_json('/data/queen_memory.json',{})
    eco=_read_json('/data/queen_ecology.json',{})
    exp=_read_json('/data/queen_experience.json',{})
    total=max(1,sum(groups.values()))
    shares=[v/total for v in groups.values()]
    hhi=sum(x*x for x in shares) if shares else 1.0
    entropy=-sum(x*math.log(x) for x in shares if x>0)
    norm_entropy=(entropy/math.log(len(shares))) if len(shares)>1 else 0.0
    effective_species=(1.0/hhi) if hhi>0 else 0.0

    prev=set()
    for x in previous_finalists or []:
        g=x.get('genome',{}); prm=g.get('parameters',{})
        key=(x.get('train',{}).get('event_signature'),x.get('validation',{}).get('event_signature'),
             int(prm.get('hold_minutes',15)),prm.get('stop_loss_pct'),prm.get('take_profit_pct'))
        prev.add(repr(key))
    behaviour_novelty=(len(signatures-prev)/max(1,len(signatures))) if signatures else 0.0
    grave=set((eco.get('graveyard') or {}).keys())
    def niche_sig(x):
        g=x.get('genome',{}); return f"h{g.get('parameters',{}).get('hold_minutes')}:"+','.join(sorted(g.get('predicates',{})))
    revisits=sum(1 for x in finalists or [] if niche_sig(x) in grave)
    hist_pref=list(mem.get('preferred_features',[]) or []); career_pref=list(exp.get('preferred_features',[]) or [])
    pref_union=set(hist_pref)|set(career_pref); pref_inter=set(hist_pref)&set(career_pref)
    career_history_agreement=(len(pref_inter)/max(1,len(pref_union))) if pref_union else 0.0
    combo_total=max(1,sum(combos.values())); combo_shares=[v/combo_total for v in combos.values()]
    combo_hhi=sum(x*x for x in combo_shares) if combo_shares else 1.0
    return {
      'tested':summary.get('tested'),'finalists':summary.get('finalists'),
      'behaviour_groups':len(groups),'largest_behaviour_fraction':max(groups.values(),default=0)/total,
      'behaviour_hhi':round(hhi,6),'behaviour_entropy':round(norm_entropy,6),'effective_behaviours':round(effective_species,2),
      'behaviour_novelty_vs_previous':round(behaviour_novelty,4),'sensor_combo_count':len(combos),'sensor_combo_hhi':round(combo_hhi,6),
      'hold_diversity':len(holds),'risk_control_diversity':len(risks),'graveyard_revisit_fraction':round(revisits/max(1,len(finalists or [])),4),
      'career_history_feature_agreement':round(career_history_agreement,4),
      'top_behaviour_group_sizes':sorted(groups.values(),reverse=True)[:8],
      'holds':dict(holds),'risk_controls':dict(risks),'top_sensors':dict(sensors.most_common(12)),
      'preferred_features':mem.get('preferred_features',[]),'underexplored_features':mem.get('underexplored_features',[]),
      'quality_history':(mem.get('quality_history',[]) or [])[-8:],'exam_history':(mem.get('exam_history',[]) or [])[-8:],
      'spartan_drought_campaigns':int(mem.get('spartan_drought_campaigns',0) or 0),
      'graveyard_niches':list((eco.get('graveyard') or {}).keys())[:20],
      'career_parent_templates':len(exp.get('parent_templates',[]) or []),
      'career_preferred_features':exp.get('preferred_features',[]),
      'prospective_experience_summary':{k:exp.get(k) for k in ('observations','career_count','eligible_careers')},
      'current_ecology_plan':summary.get('ecology_plan',{}),'sensor_availability':summary.get('sensor_availability',{}),'active_sensor_count':summary.get('active_sensor_count'),'breeding_regime_coverage':summary.get('breeding_regime_coverage',{}),
      'weak_niches':summary.get('weak_niches',[])[:12],
      'note':'breeding-visible evidence only; no holdout or Spartan answers included'}

def _bounded_research_plan(raw, e):
    # IMPORTANT: this plan feeds breeding, so it is derived ONLY from research-safe
    # evidence: Queen train/validation ecology plus prospective career evidence whose
    # mints are quarantined from validation/holdout. The executive LLM may see broader
    # operational context, but its free-form opinions never become breeding inputs.
    q=e.get('queen_research') or {}
    concentration=float(q.get('largest_behaviour_fraction',0) or 0); groups=int(q.get('behaviour_groups',0) or 0)
    hhi=float(q.get('behaviour_hhi',1) or 1); ent=float(q.get('behaviour_entropy',0) or 0); eff=float(q.get('effective_behaviours',0) or 0)
    drought=int(q.get('spartan_drought_campaigns',0) or 0)
    # Diversity pressure uses actual behavioural concentration, not just raw group count.
    if concentration>.60 or hhi>.30 or eff<5: w,a=.35,.35
    elif concentration>.35 or hhi>.15 or eff<10: w,a=.30,.30
    elif groups>=30 and concentration<.20 and ent>.75 and eff>=20: w,a=.22,.28
    else: w,a=.25,.30
    # A sustained zero-graduate streak raises search diversity, but never changes the examiner or evidence gates.
    if drought>=2:
        w=max(w,.30);a=max(a,.30)
    if drought>=5:
        w=max(w,.35);a=max(a,.30)
    try:
        from colony.queen_pattern_recognition import SENSORS
        allowed=set(SENSORS)
    except Exception: allowed=set()
    strategic=dict((e.get('strategic_guidance') or {}).get('research_adjustments') or {})
    mode=str(strategic.get('mode','balanced')).lower()
    if mode=='diversify': w=max(w,.32);a=max(a,.32)
    elif mode=='exploit' and drought==0 and groups>=20 and concentration<.25:
        w=min(w,.20);a=min(a,.25)
    exploit=1.0-w-a
    focus=[]; availability=q.get('sensor_availability') or {}
    strategic_focus=[k for k in (strategic.get('focus_sensors') or []) if k in allowed and float(availability.get(k,1.0) or 0)>=.10]
    strategic_avoid={k for k in (strategic.get('avoid_sensors') or []) if k in allowed}
    reference_focus=[k for k in ((e.get('reference_baseline') or {}).get('robust_reference_sensors') or [])
                     if k in allowed and float(availability.get(k,1.0) or 0)>=.10]
    # Reference ants are landmarks, not templates: they may nominate neglected sensors but never replace wild search.
    for k in strategic_focus+reference_focus+list(q.get('career_preferred_features',[]) or [])+list(q.get('preferred_features',[]) or [])+list(q.get('underexplored_features',[]) or []):
        if k in allowed and k not in strategic_avoid and float(availability.get(k,1.0) or 0)>=.10 and k not in focus:focus.append(k)
        if len(focus)>=8:break
    avoid=list(q.get('graveyard_niches',[]) or [])[:8]
    return {'exploit':round(exploit,4),'adjacent_explore':round(a,4),'wild_scouts':round(w,4),
            'focus_sensors':focus,'avoid_niches':avoid,'largest_behaviour_fraction':round(concentration,4),
            'behaviour_groups':groups,'behaviour_hhi':round(hhi,4),'behaviour_entropy':round(ent,4),
            'effective_behaviours':round(eff,2),'spartan_drought_campaigns':drought,'strategic_mode':mode,'strategic_focus_used':strategic_focus[:6],'reference_focus_used':reference_focus[:6],'authority':'research_allocation_only',
            'source':'research_safe_swarm_ecology'}

async def evidence(c):
    roster=[]
    rr=await c.fetchrow("SELECT run_id,stage_size,stage_index,status FROM reversal_tournament_runs ORDER BY created_at DESC LIMIT 1")
    if rr:
        x=await c.fetchrow("SELECT count(*) FILTER(WHERE active) active,count(*) FILTER(WHERE active AND baseline) controls,count(*) FILTER(WHERE active AND NOT baseline AND cohort='historical_qualified') elites FROM reversal_tournament_ants WHERE run_id=$1",rr['run_id'])
        roster.append({'family':'reversal',**dict(x),'stage':rr['stage_index'],'status':rr['status']})
    for r in await c.fetch("SELECT DISTINCT ON(family) run_id,family,stage_index,status FROM family_tournament_runs ORDER BY family,created_at DESC"):
        x=await c.fetchrow("SELECT count(*) FILTER(WHERE active) active,count(*) FILTER(WHERE active AND baseline) controls,count(*) FILTER(WHERE active AND NOT baseline AND cohort='historical_qualified') elites FROM family_tournament_ants WHERE run_id=$1",r['run_id'])
        roster.append({'family':r['family'],**dict(x),'stage':r['stage_index'],'status':r['status']})
    perf=[dict(x) for x in await c.fetch('''SELECT quote->'attribution'->>'family' family,count(*) trades,count(*) FILTER(WHERE net_pnl>0) wins,coalesce(sum(net_pnl),0) net,avg(net_pnl) FILTER(WHERE net_pnl IS NOT NULL) avg_net FROM colony_execution_ledger WHERE run_id='colony-native-v3-holdaware' AND quote->'attribution'->>'family' IN ('reversal','exhaustion','momentum','order_flow') GROUP BY 1''')]
    queue=[dict(x) for x in await c.fetch("SELECT family,count(*) waiting,max(historical_score) best FROM evolution_candidate_queue WHERE status='ready' GROUP BY family")]
    providers=[dict(x) for x in await c.fetch("SELECT DISTINCT ON(provider) provider,ok,error,observed_at FROM colony_provider_health ORDER BY provider,observed_at DESC")]
    recent=[dict(x) for x in await c.fetch("SELECT event_type,payload,created_at FROM colony_events ORDER BY id DESC LIMIT 6")]
    strategic_guidance={}
    try:
        sr=await c.fetchrow("SELECT result FROM swarm_strategy_requests WHERE status='complete' ORDER BY completed_at DESC NULLS LAST,id DESC LIMIT 1")
        if sr:
            strategic_guidance=sr['result'];strategic_guidance=json.loads(strategic_guidance) if isinstance(strategic_guidance,str) else dict(strategic_guidance or {})
    except Exception:
        strategic_guidance={}
    qrecs=await c.fetch("SELECT finalists,summary,created_at FROM historical_nursery_runs WHERE family='queen_pattern' ORDER BY created_at DESC LIMIT 2")
    refrec=await c.fetchrow("SELECT family,finalists FROM historical_nursery_runs WHERE family LIKE 'eve_reference_v%' ORDER BY created_at DESC LIMIT 1")
    reference_baseline={}
    if refrec:
        rf=refrec['finalists']; rf=json.loads(rf) if isinstance(rf,str) else list(rf or [])
        reference_baseline=_reference_baseline_snapshot(rf,refrec['family'])
    queen_research={}
    epoch=float((_read_json('/data/queen_semantic_epoch.json',{}) or {}).get('started_at',0) or 0)
    if qrecs and (not epoch or qrecs[0]['created_at'].timestamp()>=epoch):
        qrec=qrecs[0]; fs=qrec['finalists']; sm=qrec['summary']
        fs=json.loads(fs) if isinstance(fs,str) else list(fs or [])
        sm=json.loads(sm) if isinstance(sm,str) else dict(sm or {})
        prev=[]
        if len(qrecs)>1:
            pf=qrecs[1]['finalists']; prev=json.loads(pf) if isinstance(pf,str) else list(pf or [])
        queen_research=_queen_research_snapshot(fs,sm,prev)
    return {'queen_research':queen_research,'reference_baseline':reference_baseline,'performance':perf,'roster':roster,'challenger_queue':queue,'providers':providers,'recent_events':recent,'strategic_guidance':strategic_guidance,
            'queen_roles':{'version':ROLE_VERSION,'swarm':SWARM_QUEEN,'breeding':BREEDING_QUEEN},
            'constitution':{'authority':'research_director_only','real_money':False,'may_spawn_genomes':False,'may_rewrite_genetics':False,'may_relax_evidence_gates':False,
                            'may_promote_challengers':False,'shared_data':True,'isolated_colony_genetics':True,
                            'identity':'cross_market_research_director','prime_directive':'sustainable_positive_realised_net_surplus_after_all_fees_and_losses_with_bounded_drawdown',
                            'current_market_scope':SWARM_QUEEN['market_scope'],'future_scope':SWARM_QUEEN['future_scope']}}

def prompt(e):
    compact={k:e.get(k) for k in ('queen_research','reference_baseline','performance','roster','challenger_queue','providers','constitution')}
    return ("You are Swarm Queen, research director for an evolutionary trading research system. "
            "Breeding Queen alone creates and mutates genomes. You never spawn ants, trade, promote challengers, alter Spartan, lower evidence gates, use sealed holdout answers, or rewrite genomes. "
            "You are an ambitious financial organism navigating a hostile adaptive market. Assume each coin may conceal traps: examine liquidity, execution routes, adverse selection and regime changes as hostile conditions. To beat the market is to produce legitimate evidence-backed net surplus, never to control prices or interfere with others. Evolve competing research lineages, preserve capital, and propose expansion only when performance justifies resources. You cannot deploy funds or infrastructure. "
            "Survival requires repeatable positive realised surplus after fees, slippage, rent overhead and losses; never confuse paper gains with economic viability. Prioritise smaller adverse tails, executability and robustness over headline returns or raw trade count. "
            "Your job is market/regime diagnosis, research prioritisation, blind-spot detection and protection against behavioural monoculture. "
            "Return compact JSON with status, summary, material_changes, colony_notes, recommendations. "
            "Do not invent performance from roster counts. Research allocation is handled separately by deterministic research-safe logic. Evidence: "
            +json.dumps(compact,default=str,separators=(',',':'))[:2600])

async def wake(executive_inference=False):
    async with connection() as c:
        await ensure_schema(c); e=await evidence(c)
    safe_plan=_bounded_research_plan({},e)
    b={'status':'healthy','summary':'Research-safe Swarm research-director plan ready.',
       'role_version':ROLE_VERSION,'role':SWARM_QUEEN,'material_changes':[],'colony_notes':{},'recommendations':[],'research_plan':safe_plan}
    # Publish the bounded plan immediately; executive inference must never block breeding support.
    async with connection() as c:
        await ensure_schema(c)
        row_id=await c.fetchval("INSERT INTO swarm_queen_journal(model,status,briefing,input_snapshot) VALUES($1,$2,$3::jsonb,$4::jsonb) RETURNING id",
                                MODEL,'plan_ready',json.dumps(b),json.dumps(e,default=str))
    started=time.time(); state='plan_ready'
    if executive_inference:
        state='ok'
        try:
            async with httpx.AsyncClient(timeout=45) as h:
                r=await h.post(OLLAMA,json={'model':MODEL,'prompt':prompt(e),'stream':False,'format':'json','think':False,
                                           'options':{'num_ctx':1536,'num_predict':180,'temperature':0.1}})
                r.raise_for_status(); x=json.loads(r.json()['response'])
            if isinstance(x,dict):
                for k in ('status','summary','material_changes','colony_notes','recommendations'):
                    if k in x:b[k]=x[k]
        except Exception as ex:
            state='inference_error'; b['status']='warning'; b['material_changes']=[repr(ex)[:180]]
            b['recommendations']=(b.get('recommendations') or [])[:2]+['Research-safe deterministic Swarm guidance remains active.']
    b['research_plan']=safe_plan
    async with connection() as c:
        await c.execute("UPDATE swarm_queen_journal SET status=$1,briefing=$2::jsonb WHERE id=$3",state,json.dumps(b),row_id)
    return {'model':MODEL,'seconds':round(time.time()-started,2),'briefing':b}

async def latest():
    async with connection() as c:
        await ensure_schema(c); r=await c.fetchrow("SELECT observed_at,model,status,briefing FROM swarm_queen_journal ORDER BY id DESC LIMIT 1")
        return dict(r) if r else None

"""Prospective ant-career feedback for the Breeding Queen.

Only forward tournament experience is consumed. Experienced mints may inform Queen training,
but are permanently excluded from validation and holdout so career feedback can never leak
into Spartan's sealed historical examination. Active genomes remain frozen; experience
breeds descendants rather than rewriting a deployed ant in place.
"""
import json, os, statistics, time

PATH='/data/queen_experience.json'


def load_experience():
    try:
        with open(PATH) as f: return json.load(f)
    except Exception:
        return {'updated_at':0,'experienced_mints':[],'preferred_features':[],'parent_templates':[],'careers':[]}


def _genome(x):
    if isinstance(x,str):
        try:return json.loads(x)
        except Exception:return {}
    return dict(x or {})


async def learn(conn):
    # Exact hold-horizon outcomes only; one first prospective observation per ant/mint.
    rows=await conn.fetch('''
      WITH all_entries AS (
        SELECT 'reversal'::text family,e.run_id,e.genome_id,e.mint,e.candidate_id,e.observed_at,e.hold_minutes,a.genome
        FROM reversal_tournament_entries e JOIN reversal_tournament_ants a USING(run_id,genome_id)
        UNION ALL
        SELECT r.family,e.run_id,e.genome_id,e.mint,e.candidate_id,e.observed_at,e.hold_minutes,a.genome
        FROM family_tournament_entries e JOIN family_tournament_ants a USING(run_id,genome_id)
        JOIN family_tournament_runs r ON r.run_id=e.run_id
        UNION ALL
        SELECT 'eve_reference:'||r.family,r.id::text,e.genome_id,e.mint,e.candidate_id,e.observed_at,e.hold_minutes,r.genome
        FROM eve_reference_paper_entries e JOIN live_ant_registry r ON r.id=e.ant_id
        WHERE r.source='eve_reference' AND r.live_candidate=true
      ), firsts AS (
        SELECT DISTINCT ON(family,run_id,genome_id,mint) * FROM all_entries
        ORDER BY family,run_id,genome_id,mint,observed_at
      )
      SELECT f.*,o.net_return_pct FROM firsts f
      JOIN research_outcomes o ON o.candidate_id=f.candidate_id AND o.horizon_minutes=f.hold_minutes
      WHERE o.net_return_pct IS NOT NULL
      ORDER BY f.observed_at
    ''')
    by_ant={}; experienced=set()
    for r in rows:
        k=(r['family'],r['run_id'],r['genome_id']); experienced.add(r['mint'])
        z=by_ant.setdefault(k,{'family':r['family'],'run_id':r['run_id'],'genome_id':r['genome_id'],'genome':_genome(r['genome']),'returns':[],'mints':set(),'last':r['observed_at']})
        z['returns'].append(float(r['net_return_pct']));z['mints'].add(r['mint']);z['last']=max(z['last'],r['observed_at'])
    careers=[]
    for z in by_ant.values():
        vals=z.pop('returns'); mints=z.pop('mints'); n=len(vals)
        if not n: continue
        z.update(n=n,mean_return_pct=statistics.fmean(vals),median_return_pct=statistics.median(vals),win_rate=sum(v>0 for v in vals)/n,
                 worst_return_pct=min(vals),best_return_pct=max(vals),unique_mints=len(mints),last_observed_at=z['last'].isoformat())
        z.pop('last',None);careers.append(z)
    # Require a modest career before it can influence descendants. Weight support and
    # mean expectancy, while strongly penalising catastrophic careers.
    eligible=[c for c in careers if c['unique_mints']>=5]
    def career_score(c):
        mean=max(-10.0,min(10.0,float(c['mean_return_pct']))); med=max(-10.0,min(10.0,float(c['median_return_pct']))); support=min(1.0,c['unique_mints']/25.0)
        win_component=(float(c['win_rate'])-.50)*10.0
        tail=max(0.0,-float(c['worst_return_pct'])-20.0)/20.0
        robust=.45*mean+.35*med+.20*win_component
        return robust*support-tail*2.0
    for c in eligible:c['experience_score']=career_score(c)
    ranked=sorted(eligible,key=lambda c:(c['experience_score'],c['unique_mints']),reverse=True)
    feature={}
    for c in eligible:
        g=c['genome'];score=c['experience_score'];support=min(1.0,c['unique_mints']/25.0)
        for f in g.get('predicates',{}):
            q=feature.setdefault(f,{'ants':0,'events':0,'weighted_score':0.0,'positive_ants':0})
            q['ants']+=1;q['events']+=c['unique_mints'];q['weighted_score']+=score*support;q['positive_ants']+=int(c['mean_return_pct']>0)
    fr=sorted(feature.items(),key=lambda kv:(kv[1]['weighted_score']/max(1,kv[1]['ants']),kv[1]['events']),reverse=True)
    preferred=[f for f,s in fr if s['weighted_score']>0][:8]
    parents=[]
    seen=set()
    for c in ranked:
        if c['experience_score']<=0 or c['mean_return_pct']<=0 or c['median_return_pct']<0 or c['win_rate']<.50 or c['worst_return_pct']<=-25: continue
        sig=json.dumps(c['genome'],sort_keys=True,separators=(',',':'))
        if sig in seen: continue
        seen.add(sig);parents.append({'family':c['family'],'genome_id':c['genome_id'],'experience_score':c['experience_score'],'events':c['unique_mints'],'mean_return_pct':c['mean_return_pct'],'genome':c['genome']})
        if len(parents)>=24:break
    reference=[c for c in careers if str(c.get('family','')).startswith('eve_reference:')]
    # Closed live Canary outcomes inform diagnostic priorities, never parent selection
    # or validation/Spartan labels. Rent released on token-account closure is excluded.
    live=await conn.fetchrow("""SELECT count(*)::int trades,
        count(*) FILTER(WHERE (execution->>'realized_market_pnl_after_network_fees_sol')::numeric>0)::int wins,
        coalesce(sum((execution->>'realized_market_pnl_after_network_fees_sol')::numeric),0)::float8 net_sol,
        coalesce(min((execution->>'realized_market_pnl_after_network_fees_sol')::numeric),0)::float8 worst_sol
        FROM canary_trade_intents WHERE broadcast AND status='closed'
        AND execution ? 'realized_market_pnl_after_network_fees_sol'
        AND created_at>=now()-interval '7 days'""")
    economic=dict(live)
    failure={'source':'closed_broadcast_live_canary','period':'7_days','rent_recovery_excluded':True,
      'economic_result':economic,'diagnosis':'negative_net_after_network_fees' if economic['net_sol']<0 else 'insufficient_or_nonnegative',
      'research_priority':'investigate_loss_tail_entry_exit_and_liquidity_before_proposing_new_features' if economic['net_sol']<0 else 'continue_independent_prospective_validation',
      'authority':'diagnosis_only_no_genome_promotion_or_live_capital_change'}
    out={'updated_at':time.time(),'observations':len(rows),'career_count':len(careers),'eligible_careers':len(eligible),
         'experienced_mints':sorted(experienced),'preferred_features':preferred,'feature_stats':feature,
         'parent_templates':parents,'live_failure_diagnostic':failure,'careers':[{k:v for k,v in c.items() if k!='genome'} for c in ranked[:50]],
         'reference_careers':[{k:v for k,v in c.items() if k!='genome'} for c in reference],
         'reference_observations':sum(int(c.get('n') or 0) for c in reference),
         'reference_eligible_careers':sum(int(c.get('unique_mints') or 0)>=5 for c in reference)}
    os.makedirs(os.path.dirname(PATH),exist_ok=True);tmp=PATH+'.tmp'
    with open(tmp,'w') as f:json.dump(out,f,indent=2,default=str)
    os.replace(tmp,PATH)
    return out

"""Asynchronous evolutionary replenishment from historically screened candidates.
Never grants live authority and never counts historical evidence as prospective evidence.
"""
from __future__ import annotations
import json
from colony.genome import genome_id

async def seed_queue_from_latest_nursery(conn):
    out=[]
    families=('reversal','momentum','order_flow','exhaustion')
    for fam in families:
        row=await conn.fetchrow('SELECT id,finalists FROM historical_nursery_runs WHERE family=$1 ORDER BY created_at DESC LIMIT 1',fam)
        if not row: continue
        finalists=row['finalists']; finalists=json.loads(finalists) if isinstance(finalists,str) else finalists
        added=0
        for r in finalists:
            # Only queue candidates that were positive across the weighted walk-forward result.
            # Historical winners are merely allowed to audition prospectively.
            if float(r.get('robust_score',-999)) <= 0: continue
            h=r.get('holdout',{})
            # Untouched historical audit is a veto, never an optimisation target.
            if h.get('n',0)<5 or float(h.get('nursery_score',-999)) <= 0 or float(h.get('catastrophe_rate',1))>0: continue
            g=r.get('genome')
            if not g: continue
            gid=genome_id(g)
            res=await conn.execute('''INSERT INTO evolution_candidate_queue
              (family,genome_id,genome,historical_score,source_run_id,provenance)
              VALUES($1,$2,$3::jsonb,$4,$5,$6::jsonb) ON CONFLICT(family,genome_id) DO NOTHING''',
              fam,gid,json.dumps(g),float(r['robust_score']),str(row['id']),json.dumps({'source':'historical_walk_forward','proof':'discovery_only'}))
            added+=int(res.endswith('1'))
        out.append({'family':fam,'queued':added})
    return out

async def _next_candidate(conn,family,exclude):
    return await conn.fetchrow('''SELECT * FROM evolution_candidate_queue q
      WHERE family=$1 AND status='ready' AND NOT(genome_id=ANY($2::text[]))
      ORDER BY historical_score DESC, created_at ASC LIMIT 1''',family,list(exclude))


async def enforce_elite_training_only(conn):
    """Keep prospective compute/evidence focused on controls + historically qualified elites.

    Random/broad nursery organisms remain preserved in history but do not consume future
    candidate observations. The frozen baseline remains active as the control.
    """
    events=[]
    rr=await conn.fetchrow("SELECT * FROM reversal_tournament_runs WHERE status='collecting' ORDER BY created_at DESC LIMIT 1")
    if rr:
        cfg=rr['config']; cfg=json.loads(cfg) if isinstance(cfg,str) else dict(cfg or {})
        rows=await conn.fetch("SELECT genome_id,baseline,cohort FROM reversal_tournament_ants WHERE run_id=$1 AND active=true",rr['run_id'])
        allowed={'historical_qualified'}
        if cfg.get('continuous_reversal_v2'): allowed.add('forward_bred')
        drop=[r['genome_id'] for r in rows if not r['baseline'] and r['cohort'] not in allowed]
        if drop:
            await conn.execute("""UPDATE reversal_tournament_ants SET active=false,eliminated_at=now(),
              elimination_reason='elite_training_policy' WHERE run_id=$1 AND genome_id=ANY($2::text[])""",rr['run_id'],drop)
            events.append({'family':'reversal','deactivated':len(drop)})
    runs=await conn.fetch("SELECT * FROM family_tournament_runs WHERE status='collecting' ORDER BY created_at")
    for run in runs:
        rows=await conn.fetch("SELECT genome_id,baseline,cohort FROM family_tournament_ants WHERE run_id=$1 AND active=true",run['run_id'])
        drop=[r['genome_id'] for r in rows if not r['baseline'] and r['cohort']!='historical_qualified']
        if drop:
            await conn.execute("""UPDATE family_tournament_ants SET active=false,eliminated_at=now(),
              elimination_reason='elite_training_policy' WHERE run_id=$1 AND genome_id=ANY($2::text[])""",run['run_id'],drop)
            events.append({'family':run['family'],'deactivated':len(drop)})
    return events

async def replenish(conn):
    events=[]
    # Reversal tournament is separate from the other family tournaments.
    rr=await conn.fetchrow("SELECT * FROM reversal_tournament_runs WHERE status='collecting' ORDER BY created_at DESC LIMIT 1")
    if rr:
        active=await conn.fetch('SELECT genome_id FROM reversal_tournament_ants WHERE run_id=$1 AND active=true',rr['run_id'])
        # Reversal is a protected parent/control experiment. Never backfill a stage with new
        # descendants: replacements reset evidence comparability and were causing stage-0 churn.
        need=0; ids={x['genome_id'] for x in active}
        for _ in range(need):
            q=await _next_candidate(conn,'reversal',ids)
            if not q: break
            await conn.execute('''INSERT INTO reversal_tournament_ants(run_id,genome_id,genome,cohort,baseline)
              VALUES($1,$2,$3::jsonb,'historical_qualified',false) ON CONFLICT DO NOTHING''',rr['run_id'],q['genome_id'],json.dumps(q['genome']) if not isinstance(q['genome'],str) else q['genome'])
            await conn.execute("UPDATE evolution_candidate_queue SET status='deployed',deployed_at=now(),deployed_run_id=$2 WHERE id=$1",q['id'],rr['run_id'])
            ids.add(q['genome_id']); events.append({'family':'reversal','genome_id':q['genome_id'],'reason':'async_replacement'})
    runs=await conn.fetch("SELECT * FROM family_tournament_runs WHERE status='collecting' ORDER BY created_at")
    for run in runs:
        active=await conn.fetch('SELECT genome_id FROM family_tournament_ants WHERE run_id=$1 AND active=true',run['run_id'])
        need=max(0,int(run['stage_size'])-len(active)); ids={x['genome_id'] for x in active}
        for _ in range(need):
            q=await _next_candidate(conn,run['family'],ids)
            if not q: break
            g=q['genome']; g=json.loads(g) if isinstance(g,str) else g
            await conn.execute('''INSERT INTO family_tournament_ants(run_id,genome_id,genome,cohort,baseline)
              VALUES($1,$2,$3::jsonb,'historical_qualified',false) ON CONFLICT DO NOTHING''',run['run_id'],q['genome_id'],json.dumps(g))
            await conn.execute("UPDATE evolution_candidate_queue SET status='deployed',deployed_at=now(),deployed_run_id=$2 WHERE id=$1",q['id'],run['run_id'])
            ids.add(q['genome_id']); events.append({'family':run['family'],'genome_id':q['genome_id'],'reason':'async_replacement'})
    return events


async def challenger_turnover(conn):
    """Let superior queued elites replace prospectively weak incumbents without rewriting evidence.

    A challenger never displaces an ant on historical score alone. The incumbent must first
    accumulate at least 12 independent prospective mints and be prospectively non-positive.
    The challenger must also have a materially stronger historical screening score than that
    incumbent had when admitted. Baselines are never eligible for replacement.
    """
    from colony.reversal_tournament import metrics as reversal_metrics
    from colony.family_tournament import metrics as family_metrics
    events=[]

    async def maybe_rotate(family, run, table, metric_fn):
        active=await conn.fetch(f"SELECT genome_id,baseline,cohort FROM {table} WHERE run_id=$1 AND active=true",run['run_id'])
        if len(active) < int(run['stage_size']):
            return
        challenger=await _next_candidate(conn,family,{a['genome_id'] for a in active})
        if not challenger:
            return
        recs=await metric_fn(conn,run['run_id'])
        candidates=[]
        for a in active:
            if a['baseline'] or a['cohort']!='historical_qualified':
                continue
            r=recs.get(a['genome_id'],{})
            if r.get('n',0) < 12:
                continue
            prospective=float(r.get('tournament_score',-999))
            if prospective > 0:
                continue
            admitted=await conn.fetchval("SELECT historical_score FROM evolution_candidate_queue WHERE family=$1 AND genome_id=$2 ORDER BY id DESC LIMIT 1",family,a['genome_id'])
            admitted=float(admitted) if admitted is not None else 0.0
            candidates.append((prospective, admitted, a['genome_id'], r.get('n',0)))
        if not candidates:
            return
        candidates.sort(key=lambda x:(x[0],x[1]))
        prospective, admitted, loser, n = candidates[0]
        challenger_score=float(challenger['historical_score'])
        # Require a real historical advantage as well as incumbent prospective weakness.
        if challenger_score < admitted + max(0.01, abs(admitted)*0.15):
            return
        await conn.execute(f"""UPDATE {table} SET active=false,eliminated_at=now(),
          elimination_reason='challenger_displacement' WHERE run_id=$1 AND genome_id=$2""",run['run_id'],loser)
        g=challenger['genome']; g=json.loads(g) if isinstance(g,str) else g
        await conn.execute(f"""INSERT INTO {table}(run_id,genome_id,genome,cohort,baseline)
          VALUES($1,$2,$3::jsonb,'historical_qualified',false) ON CONFLICT(run_id,genome_id)
          DO UPDATE SET active=true, eliminated_at=NULL, elimination_reason=NULL, cohort='historical_qualified'""",
          run['run_id'],challenger['genome_id'],json.dumps(g))
        await conn.execute("UPDATE evolution_candidate_queue SET status='deployed',deployed_at=now(),deployed_run_id=$2 WHERE id=$1",challenger['id'],run['run_id'])
        events.append({'family':family,'out':loser,'in':challenger['genome_id'],
                       'incumbent_n':n,'incumbent_prospective_score':prospective,
                       'incumbent_historical_score':admitted,'challenger_historical_score':challenger_score})

    rr=await conn.fetchrow("SELECT * FROM reversal_tournament_runs WHERE status='collecting' ORDER BY created_at DESC LIMIT 1")
    if rr:
        # Protect Reversal baseline and frozen cohort; no asynchronous challenger displacement.
        pass
    runs=await conn.fetch("SELECT * FROM family_tournament_runs WHERE status='collecting' ORDER BY created_at")
    for run in runs:
        await maybe_rotate(run['family'],run,'family_tournament_ants',family_metrics)
    return events

async def challenger_queue_status(conn):
    rows=await conn.fetch("""SELECT family,count(*) AS waiting,max(historical_score) AS best_score
      FROM evolution_candidate_queue WHERE status='ready' GROUP BY family ORDER BY family""")
    return [dict(r) for r in rows]

async def cull_obvious_failures(conn):
    """Continuous Darwinism: remove only overwhelming failures before stage gates."""
    from colony.reversal_tournament import metrics as reversal_metrics
    from colony.family_tournament import metrics as family_metrics
    events=[]
    rr=await conn.fetchrow("SELECT * FROM reversal_tournament_runs WHERE status='collecting' ORDER BY created_at DESC LIMIT 1")
    if rr:
        recs=await reversal_metrics(conn,rr['run_id'])
        ants=await conn.fetch('SELECT genome_id,baseline FROM reversal_tournament_ants WHERE run_id=$1 AND active=true',rr['run_id'])
        expired={r['genome_id'] for r in await conn.fetch("SELECT genome_id FROM champion_league WHERE active=false")}
        losers=[]
        for a in ants:
            if a['baseline']:continue
            if a['genome_id'] in expired:
                losers.append(a['genome_id']);continue
            r=recs.get(a['genome_id'],{})
            bad=r.get('n',0)>=12 and (r.get('catastrophe_rate',0)>=.20 or (r.get('avg_return_pct',0)<=-10 and r.get('median_return_pct',0)<0) or (r.get('worst_return_pct') is not None and r['worst_return_pct']<=-50))
            if bad:losers.append(a['genome_id'])
        if losers:
            await conn.execute("UPDATE reversal_tournament_ants SET active=false,eliminated_at=now(),elimination_reason='continuous_failure_cull' WHERE run_id=$1 AND genome_id=ANY($2::text[])",rr['run_id'],losers)
            events += [{'family':'reversal','genome_id':g,'reason':'continuous_failure_cull'} for g in losers]
    runs=await conn.fetch("SELECT * FROM family_tournament_runs WHERE status='collecting' ORDER BY created_at")
    for run in runs:
        recs=await family_metrics(conn,run['run_id'])
        ants=await conn.fetch('SELECT genome_id,baseline FROM family_tournament_ants WHERE run_id=$1 AND active=true',run['run_id'])
        losers=[]
        for a in ants:
            if a['baseline']:continue
            r=recs.get(a['genome_id'],{})
            bad=r.get('n',0)>=12 and (r.get('catastrophe_rate',0)>=.20 or (r.get('avg_return_pct',0)<=-10 and r.get('median_return_pct',0)<0) or (r.get('worst_return_pct') is not None and r['worst_return_pct']<=-50))
            if bad:losers.append(a['genome_id'])
        if losers:
            await conn.execute("UPDATE family_tournament_ants SET active=false,eliminated_at=now(),elimination_reason='continuous_failure_cull' WHERE run_id=$1 AND genome_id=ANY($2::text[])",run['run_id'],losers)
            events += [{'family':run['family'],'genome_id':g,'reason':'continuous_failure_cull'} for g in losers]
    return events


async def promote_reversal_elite_to_production_pool(conn, minimum_mints=20, keep=5):
    """Promote only the best historically screened Reversal children after fresh prospective proof.

    Production-pool status means eligible for the main paper/live-ready population; it grants no
    real-money broadcast authority and never removes the existing parent generation.
    """
    from colony.reversal_tournament import metrics as reversal_metrics, rank_with_correlation, catastrophic
    run=await conn.fetchrow("SELECT * FROM reversal_tournament_runs WHERE status='collecting' ORDER BY created_at DESC LIMIT 1")
    if not run:return []
    ants=await conn.fetch("SELECT genome_id,genome,baseline,cohort FROM reversal_tournament_ants WHERE run_id=$1 AND active=true",run['run_id'])
    recs=await reversal_metrics(conn,run['run_id'])
    eligible={}
    genomes={}
    for a in ants:
        if a['baseline'] or a['cohort']!='historical_qualified':continue
        r=recs.get(a['genome_id'],{})
        if r.get('n',0)<minimum_mints or catastrophic(r):continue
        if r.get('avg_return_pct',-999)<=0 or r.get('median_return_pct',-999)<=0 or r.get('baseline_edge_pct',-999)<=0:continue
        eligible[a['genome_id']]=r; genomes[a['genome_id']]=a['genome']
    ranked=rank_with_correlation(eligible)[:keep]
    promoted=[]
    for gid,r in ranked:
        g=genomes[gid]; g=json.loads(g) if isinstance(g,str) else g
        parents=list(g.get('parents') or [])
        await conn.execute("""INSERT INTO colony_genomes(genome_id,parent_ids,generation,family,genome,status)
          VALUES($1,$2,4,'reversal',$3::jsonb,'production')
          ON CONFLICT(genome_id) DO UPDATE SET status='production'""",gid,parents,json.dumps(g))
        promoted.append({'genome_id':gid,'n':r.get('n'),'score':r.get('adjusted_score',r.get('tournament_score'))})
    return promoted

def clearly_failing_reversal_research_ant(rec):
    """Allow bounded early turnover for obvious weak performers, never sparse evidence.

    Regular mature underperformers still require 25 observations. The tighter 20-event
    early rule needs BOTH a sub-40% win rate and negative median; this is research
    turnover only, not a parent-promotion or live-capital gate.
    """
    n=int(rec.get('n', 0))
    if n < 20:
        return False
    if n >= 25:
        return (rec.get('avg_return_pct', 0) <= 0 or
                rec.get('median_return_pct', 0) <= 0 or
                rec.get('win_rate', 0) < .45)
    return rec.get('win_rate', 0) < .40 and rec.get('median_return_pct', 0) < 0


async def evolve_reversal_forward(conn, target_population=36, births_per_cycle=5, minimum_parent_mints=20):
    """Bounded forward-only breeding for the profitable Reversal lineage.

    Parents are selected only from prospective results. Children inherit genomes, never
    evidence, and must earn their own forward record. Population stays bounded so the
    Spartan/Queen search remains the primary compute consumer.
    """
    import copy, random, time, statistics
    from colony.genome import mutate, crossover, MutationPolicy, genome_id
    from colony.reversal_tournament import metrics as reversal_metrics, rank_with_correlation, catastrophic
    run=await conn.fetchrow("SELECT * FROM reversal_tournament_runs WHERE status='collecting' ORDER BY created_at DESC LIMIT 1")
    if not run:return {'run':None,'born':0}
    config=run['config']; config=json.loads(config) if isinstance(config,str) else dict(config or {})
    if not config.get('continuous_reversal_v2'):return {'run':run['run_id'],'enabled':False,'born':0}
    await conn.execute('''CREATE TABLE IF NOT EXISTS reversal_evolution_log(
      id BIGSERIAL PRIMARY KEY,run_id TEXT NOT NULL,generation INT NOT NULL,observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      active_ants INT NOT NULL,born INT NOT NULL DEFAULT 0,culled INT NOT NULL DEFAULT 0,
      parent_ids JSONB NOT NULL DEFAULT '[]'::jsonb,metrics JSONB NOT NULL DEFAULT '{}'::jsonb)''')
    for ddl in (
      "ALTER TABLE reversal_tournament_ants ADD COLUMN IF NOT EXISTS generation INT NOT NULL DEFAULT 0",
      "ALTER TABLE reversal_tournament_ants ADD COLUMN IF NOT EXISTS parent_ids JSONB NOT NULL DEFAULT '[]'::jsonb",
      "ALTER TABLE reversal_tournament_ants ADD COLUMN IF NOT EXISTS born_at TIMESTAMPTZ NOT NULL DEFAULT now()"):
        await conn.execute(ddl)
    ants=await conn.fetch("SELECT genome_id,genome,baseline,cohort,generation,born_at FROM reversal_tournament_ants WHERE run_id=$1 AND active=true",run['run_id'])
    recs=await reversal_metrics(conn,run['run_id'])
    # Protect Champion incumbents and Canary seats as research reserve; protection
    # does NOT mark them reliable parents or override any live promotion gate.
    protected_elites={r['genome_id'] for r in await conn.fetch(
        "SELECT genome_id FROM champion_league WHERE active=true AND (pool='elite' OR canary_slot IS NOT NULL)")}
    # Allow early turnover ONLY after 20 fresh observations showing both <40% wins
    # and a negative median. Ordinary mediocre ants still need the 25-event gate.
    losers=[]
    for a in ants:
        if a['baseline'] or a['genome_id'] in protected_elites: continue
        r=recs.get(a['genome_id'],{})
        if int(r.get('n',0))>=20 and (catastrophic(r) or clearly_failing_reversal_research_ant(r)):
            losers.append(a['genome_id'])
    # Avoid population collapse: at least 20 non-baseline ants survive every maintenance pass.
    max_cull=max(0,len([a for a in ants if not a['baseline']])-20)
    losers=losers[:max_cull]
    if losers:
        await conn.execute("UPDATE reversal_tournament_ants SET active=false,eliminated_at=now(),elimination_reason='continuous_v2_forward_cull' WHERE run_id=$1 AND genome_id=ANY($2::text[])",run['run_id'],losers)
    ants=[a for a in ants if a['genome_id'] not in set(losers)]
    # Parent pool requires real prospective evidence and positive centre-of-distribution.
    eligible={}
    amap={a['genome_id']:a for a in ants}
    for a in ants:
        if a['baseline']:continue
        r=recs.get(a['genome_id'],{})
        if r.get('n',0)<minimum_parent_mints or catastrophic(r):continue
        # Reproductive privilege now targets boring winners. A second, bounded repair
        # class preserves useful edge while allowing plasticity to fix a damaged tail.
        proven = (r.get('avg_return_pct',-999)>0 and r.get('median_return_pct',-999)>=.25
                  and r.get('win_rate',0)>=.55 and r.get('worst_return_pct',-999)>=-25)
        relative = (r.get('avg_return_pct',-999)>0 and r.get('median_return_pct',-999)>0
                    and r.get('baseline_edge_pct',-999)>0 and r.get('catastrophe_rate',1)<.10
                    and r.get('worst_return_pct',-999)>=-40)
        if not (proven or relative):continue
        rr=dict(r); rr['parent_class']='reliable' if proven else 'relative_tail_repair'
        eligible[a['genome_id']]=rr
    ranked=rank_with_correlation(eligible)
    # Behavioural diversity: keep parents whose opportunity sets aren't near-identical.
    parents=[]
    for gid,r in ranked:
        if all(len(r['mints'] & pr['mints'])/max(1,len(r['mints'] | pr['mints'])) < .92 for _,pr in parents):
            parents.append((gid,r))
        if len(parents)>=8:break
    # Reserve-repair fallback: if strict qualification temporarily drops to zero,
    # keep evolution alive from protected incumbent elites with substantial evidence.
    # They are explicitly NOT counted as reliable parents and get broader repair mutations.
    if not parents:
        reserve={}
        for a in ants:
            if a['genome_id'] not in protected_elites: continue
            r=recs.get(a['genome_id'],{})
            if r.get('n',0)<20 or catastrophic(r): continue
            rr=dict(r); rr['parent_class']='reserve_repair'
            reserve[a['genome_id']]=rr
        parents=rank_with_correlation(reserve)[:2]
    # Bounded rolling turnover: a full population must not freeze evolution forever.
    # At most one mature non-parent is replaced per cadence, preserving the survivor floor.
    last=await conn.fetchval("SELECT max(observed_at) FROM reversal_evolution_log WHERE run_id=$1 AND born>0",run['run_id'])
    birth_age_minutes=(time.time()-last.timestamp())/60 if last else 1e9
    if parents and len(ants)>=target_population and birth_age_minutes>=10:
        parent_ids={gid for gid,_ in parents}
        mature_replaceable={}
        for a in ants:
            if a['baseline'] or a['genome_id'] in parent_ids or a['genome_id'] in protected_elites: continue
            r=recs.get(a['genome_id'],{})
            if r.get('n',0)<25 or catastrophic(r): continue
            mature_replaceable[a['genome_id']]=r
        ranked_replaceable=rank_with_correlation(mature_replaceable)
        nonbaseline_n=sum(1 for a in ants if not a['baseline'])
        if ranked_replaceable and nonbaseline_n>20:
            turnover_gid=min(ranked_replaceable,key=lambda x:x[1].get('adjusted_score',-999))[0]
            await conn.execute("UPDATE reversal_tournament_ants SET active=false,eliminated_at=now(), elimination_reason='bounded_research_turnover' WHERE run_id=$1 AND genome_id=$2",run['run_id'],turnover_gid)
            losers.append(turnover_gid)
            ants=[a for a in ants if a['genome_id']!=turnover_gid]
            amap.pop(turnover_gid,None)
    active_ids={a['genome_id'] for a in ants}; room=max(0,target_population-len(ants)); want=min(births_per_cycle,room)
    # Rate limit births to once per ~10 minutes, unless population needs emergency refill.
    if last and room < 8 and birth_age_minutes<10:
        want=0
    born=[]; parent_used=[]
    generation=max([int(a['generation'] or 0) for a in ants] or [0])+1
    rng=random.Random(int(time.time()//1200)+generation)
    for i in range(want):
        if not parents:break
        p1=parents[i%len(parents)][0]; g1=amap[p1]['genome']; g1=json.loads(g1) if isinstance(g1,str) else dict(g1)
        if len(parents)>1 and i%3==2:
            p2=parents[(i+1)%len(parents)][0]; g2=amap[p2]['genome']; g2=json.loads(g2) if isinstance(g2,str) else dict(g2)
            child=crossover(g1,g2,seed=rng.randrange(1,10**9)); pids=[p1,p2]
            child=mutate(child,seed=rng.randrange(1,10**9),policy=MutationPolicy(numeric_sigma=.06,mutation_rate=.30,min_changes=1,max_changes=2))
            child.setdefault('plasticity',{})['mode']='crossover_balanced'
        else:
            parent_class=parents[i%len(parents)][1].get('parent_class','relative_tail_repair')
            if parent_class=='reliable':
                policy=MutationPolicy(numeric_sigma=.05,mutation_rate=.25,min_changes=1,max_changes=2)
                mode='local_exploit'
            elif parent_class=='reserve_repair':
                policy=MutationPolicy(numeric_sigma=.12,mutation_rate=.50,min_changes=1,max_changes=2)
                mode='reserve_repair_explore'
            else:
                policy=MutationPolicy(numeric_sigma=.10,mutation_rate=.45,min_changes=1,max_changes=2)
                mode='tail_repair_explore'
            child=mutate(g1,seed=rng.randrange(1,10**9),policy=policy);pids=[p1]
            child.setdefault('plasticity',{})['mode']=mode
        child['parents']=pids;child['generation']=generation;child['evolution']='reversal_continuous_v2'
        gid=genome_id(child)
        if gid in active_ids:continue
        res=await conn.execute("""INSERT INTO reversal_tournament_ants(run_id,genome_id,genome,cohort,baseline,generation,parent_ids,born_at)
          VALUES($1,$2,$3::jsonb,'forward_bred',false,$4,$5::jsonb,now()) ON CONFLICT DO NOTHING""",run['run_id'],gid,json.dumps(child),generation,json.dumps(pids))
        if res.endswith('1'):
            active_ids.add(gid);born.append(gid);parent_used.extend(pids)
    # Snapshot comparable colony health. £6 replay proxy is equal-weight simple average of compounded career returns.
    vals=[]; win_rates=[]; ns=[]; scores=[]
    for a in ants:
        if a['baseline']:continue
        r=recs.get(a['genome_id'],{})
        if not r.get('n'):continue
        vals.append(float(r.get('avg_return_pct',0)));win_rates.append(float(r.get('win_rate',0)));ns.append(int(r.get('n',0)));scores.append(float(r.get('tournament_score',-999)))
    proven_parents=sum(1 for _,r in parents if r.get('parent_class')=='reliable')
    relative_parents=sum(1 for _,r in parents if r.get('parent_class')=='relative_tail_repair')
    # Parent genome identity and the actual failed gates must accompany the count:
    # otherwise a downgrade from reliable to tail-repair looks like a deletion.
    parent_diagnostics=[]
    for gid,r in parents:
        missed=[]
        if float(r.get('avg_return_pct',-999)) <= 0: missed.append('mean_not_positive')
        if float(r.get('median_return_pct',-999)) < .25: missed.append('median_below_0.25')
        if float(r.get('win_rate',0)) < .55: missed.append('win_rate_below_55pct')
        if float(r.get('worst_return_pct',-999)) < -25: missed.append('worst_below_minus_25pct')
        parent_diagnostics.append({'genome_id':gid,'class':r.get('parent_class'),
            'n':int(r.get('n',0)),'win_rate':r.get('win_rate'),
            'median_return_pct':r.get('median_return_pct'),
            'worst_return_pct':r.get('worst_return_pct'),
            'reliable_gate_failures':missed})
    wait_reason=('no_eligible_parent' if not parents else
                 'full_population_waiting_for_evidence' if not room else
                 'birth_cadence' if want==0 else 'birth_requested')
    snap={'evidence_ants':len(vals),'median_n':statistics.median(ns) if ns else 0,'mean_avg_return_pct':statistics.fmean(vals) if vals else 0,
          'median_avg_return_pct':statistics.median(vals) if vals else 0,'mean_win_rate':statistics.fmean(win_rates) if win_rates else 0,
          'median_tournament_score':statistics.median(scores) if scores else None,'distinct_parent_behaviours':len(parents),
          'proven_parent_behaviours':proven_parents,'tail_repair_parent_behaviours':relative_parents,
          'parent_diagnostics':parent_diagnostics,'breeding_wait_reason':wait_reason,'unfilled_slots':room}
    await conn.execute("INSERT INTO reversal_evolution_log(run_id,generation,active_ants,born,culled,parent_ids,metrics) VALUES($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb)",run['run_id'],generation,len(ants)+len(born),len(born),len(losers),json.dumps(sorted(set(parent_used))),json.dumps(snap))
    return {'run':run['run_id'],'generation':generation,'active':len(ants)+len(born),'born':born,'culled':losers,'parents':sorted(set(parent_used)),'metrics':snap}

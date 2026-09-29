"""Asynchronous evolutionary replenishment from historically screened candidates.
Never grants live authority and never counts historical evidence as prospective evidence.
"""
from __future__ import annotations
import json
from colony.genome import genome_id

async def seed_queue_from_latest_nursery(conn):
    out=[]
    families=('reversal','momentum','order_flow','wallet_convergence')
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
        rows=await conn.fetch("SELECT genome_id,baseline,cohort FROM reversal_tournament_ants WHERE run_id=$1 AND active=true",rr['run_id'])
        drop=[r['genome_id'] for r in rows if not r['baseline'] and r['cohort']!='historical_qualified']
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
        need=max(0,int(rr['stage_size'])-len(active)); ids={x['genome_id'] for x in active}
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
        await maybe_rotate('reversal',rr,'reversal_tournament_ants',reversal_metrics)
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
        losers=[]
        for a in ants:
            if a['baseline']:continue
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

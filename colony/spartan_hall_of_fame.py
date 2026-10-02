"""Permanent archive of the best behaviourally distinct Spartan examinees.

Exam evidence is archival/diagnostic only. Hall-of-Fame membership never grants
prospective proof or live authority and must not feed examiner answers into Queen fitness.
"""
from __future__ import annotations
import json

KEEP_PER_EXAM = 3

async def ensure_schema(conn):
    await conn.execute("""CREATE TABLE IF NOT EXISTS spartan_hall_of_fame(
      id BIGSERIAL PRIMARY KEY,
      family TEXT NOT NULL,
      campaign INT,
      source_run_id BIGINT,
      exam_snapshot_sha256 TEXT,
      genome_id TEXT NOT NULL,
      genome JSONB NOT NULL,
      behaviour_id TEXT NOT NULL,
      exam_rank INT NOT NULL,
      qualification_pass BOOLEAN NOT NULL DEFAULT false,
      n INT NOT NULL DEFAULT 0,
      mean_raw DOUBLE PRECISION,
      opportunity_efficiency DOUBLE PRECISION,
      winner_concentration DOUBLE PRECISION,
      stress JSONB NOT NULL DEFAULT '{}'::jsonb,
      min_behavioural_distance DOUBLE PRECISION,
      archived_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
      UNIQUE(family, source_run_id, behaviour_id)
    )""")


def _score(r):
    """Rank near-misses without changing Spartan qualification rules."""
    stress=r.get('stress') or {}
    return (
        float(r.get('mean_raw') or -999.0)
        + 0.20*float(stress.get('p05_net') or -999.0)
        + 0.10*float(stress.get('cvar_10') or -999.0)
        + 0.10*float(r.get('opportunity_efficiency') or 0.0)
        - 0.10*float(r.get('winner_concentration') or 1.0)
        + 0.002*int(r.get('n') or 0)
    )


async def archive_exam(conn, family, campaign, audit, keep=KEEP_PER_EXAM):
    await ensure_schema(conn)
    row=await conn.fetchrow("SELECT id,finalists,summary FROM historical_nursery_runs WHERE family=$1 ORDER BY created_at DESC LIMIT 1",family)
    if not row:
        return {'archived':0,'reason':'no_source_run'}
    finalists=row['finalists']; finalists=json.loads(finalists) if isinstance(finalists,str) else list(finalists or [])
    summary=row['summary']; summary=json.loads(summary) if isinstance(summary,str) else dict(summary or {})
    genomes={x.get('genome_id'):x.get('genome') for x in finalists if x.get('genome_id') and x.get('genome')}

    # One representative per behaviour, then rank those representatives.
    reps={}
    for r in audit.get('results',[]):
        bid=r.get('behaviour_id') or str(tuple(r.get('events') or []))
        cur=reps.get(bid)
        if cur is None or _score(r)>_score(cur):
            reps[bid]=r
    ranked=sorted(reps.values(), key=_score, reverse=True)[:int(keep)]
    archived=[]
    for rank,r in enumerate(ranked,1):
        gid=r.get('genome_id'); g=genomes.get(gid)
        if not gid or not g:
            continue
        bid=r.get('behaviour_id') or str(tuple(r.get('events') or []))
        provenance={
            'source':'spartan_exam_archive',
            'exam_contaminated':True,
            'proof':'archival_only',
            'qualification_rules_unchanged':True,
        }
        res=await conn.execute("""INSERT INTO spartan_hall_of_fame(
          family,campaign,source_run_id,exam_snapshot_sha256,genome_id,genome,behaviour_id,exam_rank,
          qualification_pass,n,mean_raw,opportunity_efficiency,winner_concentration,stress,min_behavioural_distance,provenance)
          VALUES($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10,$11,$12,$13,$14::jsonb,$15,$16::jsonb)
          ON CONFLICT(family,source_run_id,behaviour_id) DO UPDATE SET
            exam_rank=excluded.exam_rank,qualification_pass=excluded.qualification_pass,n=excluded.n,
            mean_raw=excluded.mean_raw,opportunity_efficiency=excluded.opportunity_efficiency,
            winner_concentration=excluded.winner_concentration,stress=excluded.stress,
            min_behavioural_distance=excluded.min_behavioural_distance,provenance=excluded.provenance""",
          family,int(campaign),int(row['id']),audit.get('exam_snapshot_sha256') or summary.get('exam_snapshot_sha256'),
          gid,json.dumps(g),bid,rank,bool(r.get('qualification_pass')),int(r.get('n') or 0),
          r.get('mean_raw'),r.get('opportunity_efficiency'),r.get('winner_concentration'),json.dumps(r.get('stress') or {}),
          r.get('min_behavioural_distance'),json.dumps(provenance))
        archived.append({'genome_id':gid,'behaviour_id':bid,'rank':rank,'inserted':res.endswith('1')})
    return {'source_run_id':int(row['id']),'archived':len(archived),'members':archived}


async def archive_latest_if_new(conn, family='queen_pattern', keep=KEEP_PER_EXAM):
    await ensure_schema(conn)
    row=await conn.fetchrow("SELECT id FROM historical_nursery_runs WHERE family=$1 ORDER BY created_at DESC LIMIT 1",family)
    if not row:
        return {'archived':0,'reason':'no_source_run'}
    exists=await conn.fetchval("SELECT count(*) FROM spartan_hall_of_fame WHERE family=$1 AND source_run_id=$2",family,row['id'])
    if exists:
        return {'archived':0,'reason':'already_archived','source_run_id':int(row['id'])}
    from colony.spartan_v2_runner import audit_family
    audit=await audit_family(conn,family)
    return await archive_exam(conn,family,int(row['id']),audit,keep)

async def audit_nursery_run(conn, source_run_id, family='queen_pattern', min_events=25):
    """Recompute a historical Spartan exam for archival only; never used by Queen fitness."""
    import statistics, hashlib
    from colony.spartan_v2_runner import observations, opportunity_universe, concentration
    from colony.spartan_v2 import stress_returns, behavioural_distance, opportunity_efficiency, qualifies
    from colony.paper_economics import TARGET_STAKE_GBP, measured_roundtrip_network_fee_sol, sol_gbp_rate
    rec=await conn.fetchrow("SELECT finalists,summary FROM historical_nursery_runs WHERE id=$1 AND family=$2",source_run_id,family)
    if not rec:
        return None
    fs=rec['finalists']; fs=json.loads(fs) if isinstance(fs,str) else list(fs or [])
    summary=rec['summary']; summary=json.loads(summary) if isinstance(summary,str) else dict(summary or {})
    raw=(summary or {}).get('exam_holdout_rows') or []
    holdout=[{'mint':r['mint'],'flat':dict(r.get('flat') or {}),'returns':{int(k):float(v) for k,v in (r.get('returns') or {}).items()}} for r in raw]
    if not holdout:
        return None
    fee=await measured_roundtrip_network_fee_sol(conn); rate,_=sol_gbp_rate(); base=(fee*rate)/TARGET_STAKE_GBP
    results=[]
    for x in fs:
        g=x['genome']; obs=observations(g,holdout); rs=[r for _,_,r in obs]
        taken={i for i,_,_ in obs}; universe=opportunity_universe(g,holdout); rejected=[r for m,r in universe.items() if m not in taken]
        stress=stress_returns(rs,base,500,seed='v2:'+x['genome_id'])
        expectancy=statistics.fmean(rs) if rs else -1.0; opp=opportunity_efficiency(rs,rejected); conc=concentration(rs)
        prm=g.get('parameters',{})
        results.append({'genome_id':x['genome_id'],'events':[i for i,_,_ in obs],'n':len(rs),'mean_raw':expectancy if rs else None,
          'hold_minutes':int(prm.get('hold_minutes',15)),'stop_loss_pct':prm.get('stop_loss_pct'),'take_profit_pct':prm.get('take_profit_pct'),
          'opportunity_efficiency':opp,'winner_concentration':conc,'stress':stress.__dict__,
          'stress_pass':bool(len(rs)>=min_events and qualifies(stress,expectancy,opp,conc))})
    groups={}
    def bkey(a): return (tuple(a['events']),a['hold_minutes'],a.get('stop_loss_pct'),a.get('take_profit_pct'))
    for a in results: groups.setdefault(bkey(a),[]).append(a['genome_id'])
    for a in results:
        a['behavioural_group_size']=len(groups[bkey(a)]); a['behavioural_representative']=a['genome_id']==groups[bkey(a)][0]
        a['behaviour_id']=hashlib.sha1(repr(bkey(a)).encode()).hexdigest()[:16]
        a['qualification_pass']=bool(a['stress_pass'] and a['behavioural_representative'])
    for i,a in enumerate(results):
        a['min_behavioural_distance']=min((behavioural_distance(a['events'],b['events']) for j,b in enumerate(results) if i!=j),default=1.0)
    return {'family':family,'exam_snapshot_sha256':summary.get('exam_snapshot_sha256'),'results':results}

async def archive_specific_run(conn, source_run_id, campaign=None, family='queen_pattern', keep=KEEP_PER_EXAM):
    await ensure_schema(conn)
    rec=await conn.fetchrow("SELECT id,finalists,summary FROM historical_nursery_runs WHERE id=$1 AND family=$2",source_run_id,family)
    if not rec: return {'archived':0,'reason':'missing_run','source_run_id':source_run_id}
    audit=await audit_nursery_run(conn,source_run_id,family)
    if not audit: return {'archived':0,'reason':'no_exam_snapshot','source_run_id':source_run_id}
    finalists=rec['finalists']; finalists=json.loads(finalists) if isinstance(finalists,str) else list(finalists or [])
    genomes={x.get('genome_id'):x.get('genome') for x in finalists if x.get('genome_id') and x.get('genome')}
    reps={}
    for r in audit.get('results',[]):
        bid=r.get('behaviour_id') or str(tuple(r.get('events') or [])); cur=reps.get(bid)
        if cur is None or _score(r)>_score(cur): reps[bid]=r
    ranked=sorted(reps.values(),key=_score,reverse=True)[:int(keep)]; saved=[]
    for rank,r in enumerate(ranked,1):
        gid=r.get('genome_id'); g=genomes.get(gid)
        if not gid or not g: continue
        bid=r['behaviour_id']; prov={'source':'spartan_exam_archive','exam_contaminated':True,'proof':'archival_only','qualification_rules_unchanged':True}
        await conn.execute("""INSERT INTO spartan_hall_of_fame(family,campaign,source_run_id,exam_snapshot_sha256,genome_id,genome,behaviour_id,exam_rank,qualification_pass,n,mean_raw,opportunity_efficiency,winner_concentration,stress,min_behavioural_distance,provenance)
          VALUES($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10,$11,$12,$13,$14::jsonb,$15,$16::jsonb)
          ON CONFLICT(family,source_run_id,behaviour_id) DO UPDATE SET exam_rank=excluded.exam_rank,genome_id=excluded.genome_id,genome=excluded.genome,qualification_pass=excluded.qualification_pass,n=excluded.n,mean_raw=excluded.mean_raw,opportunity_efficiency=excluded.opportunity_efficiency,winner_concentration=excluded.winner_concentration,stress=excluded.stress,min_behavioural_distance=excluded.min_behavioural_distance,provenance=excluded.provenance""",
          family,campaign,int(source_run_id),audit.get('exam_snapshot_sha256'),gid,json.dumps(g),bid,rank,bool(r.get('qualification_pass')),int(r.get('n') or 0),r.get('mean_raw'),r.get('opportunity_efficiency'),r.get('winner_concentration'),json.dumps(r.get('stress') or {}),r.get('min_behavioural_distance'),json.dumps(prov))
        saved.append({'rank':rank,'genome_id':gid,'behaviour_id':bid,'n':r.get('n'),'mean_raw':r.get('mean_raw')})
    return {'source_run_id':int(source_run_id),'archived':len(saved),'members':saved}

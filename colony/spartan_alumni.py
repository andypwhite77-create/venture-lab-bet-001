"""Quarantined paper breeding pool for dead Spartan finalists.
Exam evidence may nominate ancestry, but never counts as proof. All selection below is prospective-only.
"""
from __future__ import annotations
import copy, json, random, statistics
from colony.forward import eligible
from colony.genome import genome_id, mutate, MutationPolicy
from colony.paper_economics import TARGET_STAKE_GBP, adjusted_return_pct, measured_roundtrip_network_fee_sol, sol_gbp_rate
from colony.selection import ant_metrics
from research_db import request_candidate_outcome

MIN_COMPARE_N=12
TARGET_ACTIVE=24
BIRTHS_PER_CYCLE=3
HOLD_MINUTES_MIN=3
HOLD_MINUTES_MAX=240
HOLD_PROBE_HORIZONS=(3,4,6,8,15,30)
HOLD_PROBE_TARGET=len(HOLD_PROBE_HORIZONS)

def bound_hold_minutes(value:int)->int:
    return max(HOLD_MINUTES_MIN,min(HOLD_MINUTES_MAX,int(value)))

async def ensure_schema(conn):
    await conn.execute("""CREATE TABLE IF NOT EXISTS spartan_alumni_pool(
      genome_id TEXT PRIMARY KEY, genome JSONB NOT NULL, family TEXT NOT NULL, source_run_id BIGINT,
      source_behaviour_id TEXT, source_rank INT, role TEXT NOT NULL, contaminated_snapshot TEXT,
      generation INT NOT NULL DEFAULT 0, parent_ids JSONB NOT NULL DEFAULT '[]'::jsonb, active BOOLEAN NOT NULL DEFAULT true,
      born_at TIMESTAMPTZ NOT NULL DEFAULT now(), retired_at TIMESTAMPTZ, retirement_reason TEXT)""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS spartan_alumni_entries(
      id BIGSERIAL PRIMARY KEY, genome_id TEXT NOT NULL REFERENCES spartan_alumni_pool(genome_id), mint TEXT NOT NULL,
      candidate_id BIGINT NOT NULL, observed_at TIMESTAMPTZ NOT NULL, hold_minutes INT NOT NULL, UNIQUE(genome_id,candidate_id))""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS spartan_alumni_state(
      key TEXT PRIMARY KEY,value JSONB NOT NULL DEFAULT '{}'::jsonb,updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")

async def process(conn):
    await ensure_schema(conn)
    state=await conn.fetchrow("SELECT value FROM spartan_alumni_state WHERE key='cursor'")
    val=state['value'] if state else {}; val=json.loads(val) if isinstance(val,str) else dict(val or {})
    last=int(val.get('last_candidate_id',0))
    ants=await conn.fetch("SELECT genome_id,genome,born_at FROM spartan_alumni_pool WHERE active=true")
    rows=await conn.fetch("SELECT id,created_at,mint,features,market FROM research_candidates WHERE id>$1 ORDER BY id",last)
    ins=0
    for row in rows:
        r=dict(row)
        for a in ants:
            g=a['genome']; g=json.loads(g) if isinstance(g,str) else g
            if r['created_at'] < a['born_at']: continue
            prev=await conn.fetchval("SELECT max(observed_at) FROM spartan_alumni_entries WHERE genome_id=$1 AND mint=$2",a['genome_id'],r['mint'])
            if not eligible(g,r,prev): continue
            hold=bound_hold_minutes(int(g.get('parameters',{}).get('hold_minutes',15)))
            res=await conn.execute("""INSERT INTO spartan_alumni_entries(genome_id,mint,candidate_id,observed_at,hold_minutes)
              VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING""",a['genome_id'],r['mint'],r['id'],r['created_at'],hold)
            inserted=int(res.endswith('1'))
            if inserted:
                await request_candidate_outcome(conn,r['id'],hold,'spartan_alumni')
            ins+=inserted
    if rows:
        await conn.execute("INSERT INTO spartan_alumni_state(key,value,updated_at) VALUES('cursor',jsonb_build_object('last_candidate_id',$1::bigint),now()) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=now()",rows[-1]['id'])
    return {'active':len(ants),'candidates':len(rows),'inserted':ins,'last_candidate_id':rows[-1]['id'] if rows else last}

async def metrics(conn):
    fee=await measured_roundtrip_network_fee_sol(conn); rate,_=sol_gbp_rate(); fixed=fee*rate
    rows=await conn.fetch("""SELECT e.genome_id,e.mint,e.observed_at,o.net_return_pct
      FROM spartan_alumni_entries e JOIN research_outcomes o ON o.candidate_id=e.candidate_id AND o.horizon_minutes=e.hold_minutes
      ORDER BY e.genome_id,e.observed_at""")
    by={}
    for r in rows: by.setdefault(r['genome_id'],{}).setdefault(r['mint'],float(r['net_return_pct']))
    out={}
    for gid,m in by.items():
        adj={k:adjusted_return_pct(v,TARGET_STAKE_GBP,fixed) for k,v in m.items()}
        mm=ant_metrics(list(adj.items())); vals=list(adj.values()); pos=[x for x in vals if x>0]
        mm.update({'mints':adj,'worst_return_pct':min(vals) if vals else None,
                   'winner_concentration':(max(pos)/sum(pos) if pos and sum(pos)>0 else 1.0)})
        out[gid]=mm
    return out

def spartan_evidence_leaders(recs):
    """Keep independent evidence maxima attached to their own genomes.

    Most observations and highest average return are not necessarily the same ant;
    never combine their values into a fictitious best performer.
    """
    rows=[(gid,r) for gid,r in recs.items() if int(r.get('n',0))>0]
    by_n=sorted(rows,key=lambda x:(-int(x[1]['n']),-float(x[1].get('avg_return_pct') if x[1].get('avg_return_pct') is not None else -999),x[0]))
    by_avg=sorted(rows,key=lambda x:(-float(x[1].get('avg_return_pct') if x[1].get('avg_return_pct') is not None else -999),-int(x[1]['n']),x[0]))
    def detail(pair):
        if not pair:return None
        gid,r=pair
        return {'genome_id':gid,'n':int(r.get('n',0)),
                'avg_return_pct':r.get('avg_return_pct'),
                'median_return_pct':r.get('median_return_pct'),
                'worst_return_pct':r.get('worst_return_pct')}
    return {'most_observations':detail(by_n[0] if by_n else None),
            'highest_average':detail(by_avg[0] if by_avg else None)}


async def evolve(conn):
    await ensure_schema(conn)
    recs=await metrics(conn)
    ants=await conn.fetch("SELECT genome_id,genome,generation,parent_ids,role,active FROM spartan_alumni_pool WHERE active=true")
    amap={a['genome_id']:a for a in ants}; culled=[]
    # Wood chipper: descendants must beat direct parent on paired fresh mints.
    for a in ants:
        if int(a['generation'])<=0: continue
        parents=a['parent_ids']; parents=json.loads(parents) if isinstance(parents,str) else list(parents or [])
        if not parents: continue
        cr=recs.get(a['genome_id'],{}); cg=cr.get('mints',{})
        if cr.get('n',0)<MIN_COMPARE_N: continue
        parent_scores=[]
        for pid in parents:
            pr=recs.get(pid,{}); pg=pr.get('mints',{}); shared=sorted(set(cg)&set(pg))
            if len(shared)<MIN_COMPARE_N: continue
            child_mean=statistics.fmean(cg[m] for m in shared); parent_mean=statistics.fmean(pg[m] for m in shared)
            parent_scores.append((child_mean-parent_mean,pr.get('worst_return_pct'),pr.get('winner_concentration')))
        if not parent_scores: continue
        best_delta=max(x[0] for x in parent_scores)
        parent_worst=max((x[1] for x in parent_scores if x[1] is not None),default=None)
        parent_conc=min((x[2] for x in parent_scores if x[2] is not None),default=1.0)
        tail_worse=(parent_worst is not None and cr.get('worst_return_pct') is not None and cr['worst_return_pct'] < parent_worst-5)
        conc_worse=cr.get('winner_concentration',1.0) > parent_conc+0.10
        if best_delta<=0 or tail_worse or conc_worse:
            await conn.execute("UPDATE spartan_alumni_pool SET active=false,retired_at=now(),retirement_reason=$2 WHERE genome_id=$1",a['genome_id'],'failed_parent_improvement')
            culled.append(a['genome_id'])
    ants=await conn.fetch("SELECT genome_id,genome,generation,role FROM spartan_alumni_pool WHERE active=true")
    active_ids={a['genome_id'] for a in ants}; candidates=[]
    for a in ants:
        r=recs.get(a['genome_id'],{})
        if r.get('n',0)<MIN_COMPARE_N: continue
        avg=float(r.get('avg_return_pct',-999)); med=float(r.get('median_return_pct',-999)); conc=float(r.get('winner_concentration',1))
        score=avg + .35*med - .25*max(0,conc-.45)*100
        if avg>0 and med>0: candidates.append((score,a))
    candidates.sort(reverse=True,key=lambda x:x[0])
    born=[]; rng=random.Random('spartan-alumni:'+str(await conn.fetchval('select coalesce(max(id),0) from spartan_alumni_entries')))

    # Preserve a small controlled lane whose only experimental variable is hold time.
    slots=max(0,TARGET_ACTIVE-len(ants))
    active_probe_holds={int((json.loads(a['genome']) if isinstance(a['genome'],str) else a['genome']).get('parameters',{}).get('hold_minutes',15))
                        for a in ants if a['role']=='hold_probe'}
    missing_probe_holds=[h for h in HOLD_PROBE_HORIZONS if h not in active_probe_holds]
    probe_parents=[]
    for a in ants:
        if a['role']=='hold_probe': continue
        r=recs.get(a['genome_id'],{})
        if r.get('n',0)>=5 and float(r.get('avg_return_pct',-999))>0:
            probe_parents.append((float(r['avg_return_pct']),int(r['n']),a))
    probe_parents.sort(reverse=True,key=lambda x:(x[0],x[1]))
    if slots and missing_probe_holds and probe_parents:
        _,_,p=probe_parents[0]; g=p['genome']; g=json.loads(g) if isinstance(g,str) else g
        h=missing_probe_holds[0]; child=copy.deepcopy(g)
        child.setdefault('parameters',{})['hold_minutes']=h
        child['parents']=[p['genome_id']]
        child['mutation']={'parent':p['genome_id'],'seed':None,'changed':['hold_minutes'],'experiment':'hold_time_probe'}
        child['spartan_alumni']={'ancestry':'exam_contaminated','proof':'prospective_only','experiment':'hold_time_probe',
                                 'baseline_hold':int(g.get('parameters',{}).get('hold_minutes',15)),'probe_hold':h}
        cid=genome_id(child)
        if cid not in active_ids:
            res=await conn.execute("""INSERT INTO spartan_alumni_pool(genome_id,genome,family,role,generation,parent_ids)
              VALUES($1,$2::jsonb,'exhaustion','hold_probe',$3,$4::jsonb) ON CONFLICT DO NOTHING""",
              cid,json.dumps(child),int(p['generation'])+1,json.dumps([p['genome_id']]))
            if res.endswith('1'):
                born.append(cid); active_ids.add(cid); slots-=1

    births=min(BIRTHS_PER_CYCLE,slots,len(candidates))
    for _,p in candidates[:births]:
        g=p['genome']; g=json.loads(g) if isinstance(g,str) else g
        child=mutate(g,seed=rng.randrange(2**31),policy=MutationPolicy(numeric_sigma=.10,mutation_rate=.5,min_changes=1,max_changes=2))
        if 'hold_minutes' in child.get('parameters',{}):
            child['parameters']['hold_minutes']=bound_hold_minutes(child['parameters']['hold_minutes'])
        child['parents']=[p['genome_id']]; child['spartan_alumni']={'ancestry':'exam_contaminated','proof':'prospective_only'}
        cid=genome_id(child)
        if cid in active_ids: continue
        res=await conn.execute("""INSERT INTO spartan_alumni_pool(genome_id,genome,family,role,generation,parent_ids)
          VALUES($1,$2::jsonb,'exhaustion','prospective_child',$3,$4::jsonb) ON CONFLICT DO NOTHING""",cid,json.dumps(child),int(p['generation'])+1,json.dumps([p['genome_id']]))
        if res.endswith('1'): born.append(cid); active_ids.add(cid)
    leaders=spartan_evidence_leaders(recs)
    summary={'active':await conn.fetchval('select count(*) from spartan_alumni_pool where active'),
             'evidence_ants':sum(1 for r in recs.values() if r.get('n',0)>0),'culled':culled,'born':born,
             'best_n':leaders['most_observations']['n'] if leaders['most_observations'] else 0,
             'best_avg_return_pct':leaders['highest_average']['avg_return_pct'] if leaders['highest_average'] else None,
             **leaders}
    await conn.execute("INSERT INTO spartan_alumni_state(key,value,updated_at) VALUES('last_evolution',$1::jsonb,now()) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=now()",json.dumps(summary))
    return summary

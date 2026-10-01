"""Queen brood lifecycle: nursery -> paper -> live-ready. No live execution authority."""
import hashlib, json
from db import connection
from colony.genome import mutate, genome_id, MutationPolicy
from colony.forward import eligible

NURSERY_MIN_HOURS=12
NURSERY_MIN_EVIDENCE=10
NURSERY_MIN_CONTROLS=5
PAPER_MIN_HOURS=48
PAPER_MIN_EVIDENCE=50
PAPER_MIN_CONTROLS=30
MAX_NURSERY_PER_BLOODLINE=40
GLOBAL_NURSERY_CAP=50
GRAVEYARD_MIN_EVIDENCE=20
GRAVEYARD_MIN_PARENT_WINDOW=10
GRAVEYARD_BAD_ABSOLUTE_PCT=0.0
GRAVEYARD_BAD_EDGE_PCT=-2.0
NEAR_FAILURE_DISTANCE=0.08
NEAR_FAILURE_NEIGHBORS=3
BLOODLINE_QUALIFY_N=20
ELITE_PARENT_FRACTION=0.10
ELITE_PARITY_TOLERANCE_PCT=0.50
BLOODLINE_IMPROVEMENT_MARGIN_PCT=0.0

MUTATION_CLASSES=(
    ('local', MutationPolicy(numeric_sigma=0.08, mutation_rate=0.20, min_changes=1, max_changes=2)),
    ('standard', MutationPolicy(numeric_sigma=0.12, mutation_rate=0.35, min_changes=1, max_changes=3)),
    ('wide', MutationPolicy(numeric_sigma=0.25, mutation_rate=0.55, min_changes=2, max_changes=4)),
    ('exploratory', MutationPolicy(numeric_sigma=0.40, mutation_rate=0.80, min_changes=2, max_changes=6)),
)

def _phenotype_payload(genome):
    # Functional identity excludes ancestry/provenance metadata.
    return {k:v for k,v in genome.items() if k not in ('mutation','parents')}

def phenotype_id(genome):
    raw=json.dumps(_phenotype_payload(genome),sort_keys=True,separators=(',',':'))
    return 'p_'+hashlib.sha256(raw.encode()).hexdigest()[:16]

def _parameter_distance(a,b):
    """Scale-free mean distance across shared numeric parameters."""
    ap=a.get('parameters',{}); bp=b.get('parameters',{})
    keys=[k for k in set(ap)&set(bp) if isinstance(ap[k],(int,float)) and not isinstance(ap[k],bool) and isinstance(bp[k],(int,float)) and not isinstance(bp[k],bool)]
    if not keys: return 1.0
    ds=[]
    for k in keys:
        av=float(ap[k]); bv=float(bp[k]); scale=max(abs(av),abs(bv),1.0)
        ds.append(abs(av-bv)/scale)
    return sum(ds)/len(ds)

async def ensure_schema():
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_queen_scouts(
          id BIGSERIAL PRIMARY KEY,mind_experiment_id BIGINT NOT NULL,run_id TEXT NOT NULL,
          parent_genome_id TEXT NOT NULL,genome_id TEXT NOT NULL,genome JSONB NOT NULL,
          birth_cutoff BIGINT NOT NULL,created_at TIMESTAMPTZ DEFAULT now(),state TEXT NOT NULL DEFAULT 'nursery',
          stage_updated_at TIMESTAMPTZ DEFAULT now(),stage_reason TEXT,phenotype_id TEXT,
          UNIQUE(mind_experiment_id,genome_id))''')
        await c.execute("ALTER TABLE colony_queen_scouts ADD COLUMN IF NOT EXISTS stage_updated_at TIMESTAMPTZ DEFAULT now()")
        await c.execute("ALTER TABLE colony_queen_scouts ADD COLUMN IF NOT EXISTS stage_reason TEXT")
        await c.execute("ALTER TABLE colony_queen_scouts ADD COLUMN IF NOT EXISTS phenotype_id TEXT")
        await c.execute("UPDATE colony_queen_scouts SET state='nursery' WHERE state='shadow'")
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_queen_scout_entries(
          id BIGSERIAL PRIMARY KEY,scout_id BIGINT NOT NULL REFERENCES colony_queen_scouts(id),
          mint TEXT NOT NULL,candidate_id BIGINT NOT NULL,observed_at TIMESTAMPTZ NOT NULL,
          hold_minutes INTEGER NOT NULL,UNIQUE(scout_id,candidate_id))''')
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_genome_graveyard(
          phenotype_id TEXT PRIMARY KEY,genome_id TEXT NOT NULL,parent_genome_id TEXT,family TEXT NOT NULL,
          genome JSONB NOT NULL,reason TEXT NOT NULL,evidence_n INTEGER,parent_window_n INTEGER,
          mean_return_pct DOUBLE PRECISION,edge_vs_parent_pct DOUBLE PRECISION,created_at TIMESTAMPTZ DEFAULT now())''')
        rows=await c.fetch("SELECT id,genome FROM colony_queen_scouts WHERE phenotype_id IS NULL")
        for r in rows:
            g=r['genome'] if isinstance(r['genome'],dict) else json.loads(r['genome'])
            await c.execute("UPDATE colony_queen_scouts SET phenotype_id=$2 WHERE id=$1",r['id'],phenotype_id(g))
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_queen_scout_lifecycle(
          id BIGSERIAL PRIMARY KEY,scout_id BIGINT NOT NULL REFERENCES colony_queen_scouts(id),
          from_state TEXT,to_state TEXT NOT NULL,reason TEXT NOT NULL,created_at TIMESTAMPTZ DEFAULT now())''')
        # Preserve historical duplicates as research memory but stop spending new evidence on them.
        dupes=await c.fetch('''SELECT phenotype_id,array_agg(id ORDER BY id) ids FROM colony_queen_scouts
          WHERE phenotype_id IS NOT NULL AND state IN ('nursery','paper') GROUP BY phenotype_id HAVING count(*)>1''')
        for d in dupes:
            for sid in list(d['ids'])[1:]:
                old=await c.fetchval("SELECT state FROM colony_queen_scouts WHERE id=$1",sid)
                await c.execute("UPDATE colony_queen_scouts SET state='research_archive',stage_updated_at=now(),stage_reason='exact_duplicate_existing' WHERE id=$1",sid)
                exists=await c.fetchval("SELECT EXISTS(SELECT 1 FROM colony_queen_scout_lifecycle WHERE scout_id=$1 AND to_state='research_archive' AND reason='exact_duplicate_existing')",sid)
                if not exists:
                    await c.execute("INSERT INTO colony_queen_scout_lifecycle(scout_id,from_state,to_state,reason) VALUES($1,$2,'research_archive','exact_duplicate_existing')",sid,old)

async def active_count(family=None):
    await ensure_schema()
    async with connection() as c:
        if family:
            return int(await c.fetchval("SELECT count(*) FROM colony_queen_scouts WHERE state='nursery' AND genome->>'family'=$1",family))
        return int(await c.fetchval("SELECT count(*) FROM colony_queen_scouts WHERE state='nursery'"))

def _seed(experiment_id,parent_id,slot):
    return int(hashlib.sha256(f'queen:{experiment_id}:{parent_id}:{slot}'.encode()).hexdigest()[:8],16)

async def create(experiment_id,run_id,cutoff,parent_ids,max_scouts=2):
    """Create a bounded, diverse nursery brood from grounded generation-3 parents."""
    await ensure_schema(); made=[]
    parent_ids=list(dict.fromkeys(parent_ids or []))
    async with connection() as c:
        rows=await c.fetch("SELECT genome_id,family,genome FROM colony_genomes WHERE genome_id=ANY($1::text[]) AND generation=3",parent_ids)
        found={r['genome_id']:r for r in rows}; parent_ids=[p for p in parent_ids if p in found]
        families=[found[p]['family'] for p in parent_ids]
        if not families: return {'created':0,'scouts':[],'mode':'shadow_only','why':'no_grounded_parents'}
        if len(set(families))!=1: return {'created':0,'scouts':[],'mode':'shadow_only','why':'one_bloodline_per_brood'}
        family=families[0]
        nursery_n=int(await c.fetchval("SELECT count(*) FROM colony_queen_scouts WHERE state='nursery' AND genome->>'family'=$1",family) or 0)
        global_n=int(await c.fetchval("SELECT count(*) FROM colony_queen_scouts WHERE state='nursery'") or 0)
        family_room=max(0,MAX_NURSERY_PER_BLOODLINE-nursery_n)
        global_room=max(0,GLOBAL_NURSERY_CAP-global_n)
        mature_n=int(await c.fetchval("SELECT count(*) FROM colony_genomes WHERE generation=3 AND family=$1",family) or 0)
        descendants_n=int(await c.fetchval("SELECT count(*) FROM colony_queen_scouts WHERE state IN ('nursery','paper','live_ready') AND genome->>'family'=$1",family) or 0)
        population_room=max(0,50-mature_n-descendants_n)
        target=min(int(max_scouts or 0),family_room,global_room,population_room)
        if target<=0:
            why='global_nursery_cap' if global_room<=0 else ('bloodline_nursery_cap' if family_room<=0 else 'bloodline_population_cap')
            return {'created':0,'scouts':[],'mode':'shadow_only','why':why,'family':family,
                    'nursery_cap':MAX_NURSERY_PER_BLOODLINE,'global_cap':GLOBAL_NURSERY_CAP,'population_cap':50}
        attempts=0
        while len(made)<target and attempts<target*12:
            pid=parent_ids[attempts % len(parent_ids)]
            parent=found[pid]['genome'] if isinstance(found[pid]['genome'],dict) else json.loads(found[pid]['genome'])
            class_name,policy=MUTATION_CLASSES[attempts % len(MUTATION_CLASSES)]
            child=mutate(parent,seed=_seed(experiment_id,pid,attempts),policy=policy)
            child.setdefault('mutation',{})['class']=class_name
            gid=genome_id(child); phid=phenotype_id(child)
            # Exact functional duplicates never return, regardless of mutation seed/provenance.
            seen=await c.fetchval("SELECT EXISTS(SELECT 1 FROM colony_queen_scouts WHERE phenotype_id=$1) OR EXISTS(SELECT 1 FROM colony_genome_graveyard WHERE phenotype_id=$1)",phid)
            if seen:
                attempts+=1; continue
            # Repeated nearby failures make a region hostile; one isolated failure does not.
            graves=await c.fetch("SELECT genome FROM colony_genome_graveyard WHERE family=$1",family)
            near=0
            for gr in graves:
                gg=gr['genome'] if isinstance(gr['genome'],dict) else json.loads(gr['genome'])
                if _parameter_distance(child,gg)<=NEAR_FAILURE_DISTANCE: near+=1
            if near>=NEAR_FAILURE_NEIGHBORS:
                attempts+=1; continue
            sid=await c.fetchval('''INSERT INTO colony_queen_scouts
              (mind_experiment_id,run_id,parent_genome_id,genome_id,genome,birth_cutoff,state,stage_reason,phenotype_id)
              VALUES($1,$2,$3,$4,$5::jsonb,$6,'nursery',$7,$8) ON CONFLICT DO NOTHING RETURNING id''',
              experiment_id,run_id,pid,gid,json.dumps(child),int(cutoff or 0),f'newborn_qc:{class_name}',phid)
            if sid:
                await c.execute("INSERT INTO colony_queen_scout_lifecycle(scout_id,from_state,to_state,reason) VALUES($1,NULL,'nursery',$2)",sid,f'newborn_qc:{class_name}')
                made.append({'scout_id':sid,'genome_id':gid,'parent':pid,'mutation_class':class_name})
            attempts+=1
    return {'created':len(made),'scouts':made,'mode':'shadow_only','stage':'nursery','family':family,
            'requested':int(max_scouts or 0),'caps':{'family_nursery':MAX_NURSERY_PER_BLOODLINE,'global_nursery':GLOBAL_NURSERY_CAP,'bloodline_population':50}}

async def process():
    await ensure_schema(); inserted=0
    async with connection() as c:
        scouts=await c.fetch("SELECT id,genome,birth_cutoff FROM colony_queen_scouts WHERE state IN ('nursery','paper')")
        for s in scouts:
            g=s['genome'] if isinstance(s['genome'],dict) else json.loads(s['genome'])
            rows=await c.fetch("SELECT id,created_at,mint,features,market FROM research_candidates WHERE id>$1 ORDER BY id",s['birth_cutoff'])
            for row in rows:
                r=dict(row); prev=await c.fetchval("SELECT max(observed_at) FROM colony_queen_scout_entries WHERE scout_id=$1 AND mint=$2",s['id'],r['mint'])
                if not eligible(g,r,prev): continue
                hold=int(g.get('parameters',{}).get('hold_minutes',15))
                x=await c.execute('''INSERT INTO colony_queen_scout_entries(scout_id,mint,candidate_id,observed_at,hold_minutes)
                  VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING''',s['id'],r['mint'],r['id'],r['created_at'],hold)
                inserted += int(x.endswith('1'))
    return {'active_brood':len(scouts),'inserted':inserted}
async def _metrics(c,scout_id,parent_id):
    # One measured observation per mint is treated as one independent child opportunity.
    # Exact same-candidate overlap is reported separately from the parent's whole
    # prospective window, because eligibility mutations can intentionally add/remove trades.
    child_rows=await c.fetch('''SELECT DISTINCT ON (e.mint) e.mint,e.candidate_id,e.observed_at,e.hold_minutes,o.net_return_pct
      FROM colony_queen_scout_entries e JOIN LATERAL
      (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=e.candidate_id AND measured_at>=e.observed_at AND horizon_minutes=e.hold_minutes LIMIT 1) o ON true
      WHERE e.scout_id=$1 AND o.net_return_pct IS NOT NULL ORDER BY e.mint,e.observed_at''',scout_id)
    child_vals=[float(r['net_return_pct']) for r in child_rows]
    evidence_n=len(child_vals)
    cm=sum(child_vals)/evidence_n if evidence_n else None
    worst=min(child_vals) if child_vals else None

    paired=[]
    for ce in child_rows:
        pe=await c.fetchrow('''SELECT observed_at,hold_minutes FROM colony_forward_entries
          WHERE genome_id=$1 AND candidate_id=$2 ORDER BY observed_at LIMIT 1''',parent_id,ce['candidate_id'])
        if not pe: continue
        po=await c.fetchval('''SELECT net_return_pct FROM research_outcomes
          WHERE candidate_id=$1 AND measured_at>=$2 AND horizon_minutes=$3 LIMIT 1''',
          ce['candidate_id'],pe['observed_at'],pe['hold_minutes'])
        if po is not None: paired.append((float(ce['net_return_pct']),float(po)))
    pn=len(paired)
    pcm=sum(x for x,_ in paired)/pn if pn else None
    pm=sum(y for _,y in paired)/pn if pn else None
    delta=sum(x-y for x,y in paired)/pn if pn else None

    parent_rows=await c.fetch('''SELECT DISTINCT ON (pe.mint) pe.mint,po.net_return_pct
      FROM colony_forward_entries pe JOIN colony_queen_scouts s ON s.id=$2
      JOIN LATERAL (SELECT net_return_pct FROM research_outcomes
        WHERE candidate_id=pe.candidate_id AND measured_at>=pe.observed_at AND horizon_minutes=pe.hold_minutes LIMIT 1) po ON true
      WHERE pe.genome_id=$1 AND pe.candidate_id>s.birth_cutoff AND po.net_return_pct IS NOT NULL
      ORDER BY pe.mint,pe.observed_at''',parent_id,scout_id)
    parent_vals=[float(r['net_return_pct']) for r in parent_rows]
    pwn=len(parent_vals)
    pwm=sum(parent_vals)/pwn if pwn else None
    window_edge=(cm-pwm) if cm is not None and pwm is not None else None
    return {'evidence_n':evidence_n,'mean_return_pct':cm,'worst_return_pct':worst,
            'paired_n':pn,'control_n':pn,'novel_n':max(0,evidence_n-pn),
            'paired_child_mean_return_pct':pcm,'parent_mean_return_pct':pm,
            'mean_paired_delta_pct':delta,'edge_vs_parent_pct':delta,
            'paired_wins':sum(x>y for x,y in paired),'paired_losses':sum(x<y for x,y in paired),'paired_ties':sum(x==y for x,y in paired),
            'parent_window_n':pwn,'parent_window_mean_return_pct':pwm,'window_edge_vs_parent_pct':window_edge}

async def _bloodline_reference(c,family,parent_id):
    # Mature baseline = median prospective mean return of evidence-qualified Gen-3 adults.
    rows=await c.fetch('''SELECT g.genome_id,e.mint,o.net_return_pct
      FROM colony_genomes g JOIN colony_forward_entries e ON e.genome_id=g.genome_id
      JOIN LATERAL (SELECT net_return_pct FROM research_outcomes
        WHERE candidate_id=e.candidate_id AND measured_at>=e.observed_at AND horizon_minutes=e.hold_minutes LIMIT 1) o ON true
      WHERE g.generation=3 AND g.family=$1 AND e.run_id=$2 AND o.net_return_pct IS NOT NULL''',family,'fwd-g3-20260926T084022Z')
    by={}
    for r in rows:
        by.setdefault(r['genome_id'],{}).setdefault(r['mint'],float(r['net_return_pct']))
    adults=[]
    for gid,mints in by.items():
        vals=list(mints.values())
        if len(vals)>=BLOODLINE_QUALIFY_N:
            adults.append((gid,len(vals),sum(vals)/len(vals)))
    if not adults:
        return {'bloodline_baseline_pct':None,'qualified_adults':0,'parent_rank':None,'parent_percentile':None,'elite_parent':False,'parent_lifetime_mean_pct':None}
    means=sorted(x[2] for x in adults)
    n=len(means); mid=n//2
    baseline=means[mid] if n%2 else (means[mid-1]+means[mid])/2
    ranked=sorted(adults,key=lambda x:x[2],reverse=True)
    parent=next((x for x in ranked if x[0]==parent_id),None)
    rank=(ranked.index(parent)+1) if parent else None
    elite_slots=max(1,__import__('math').ceil(len(ranked)*ELITE_PARENT_FRACTION))
    return {'bloodline_baseline_pct':baseline,'qualified_adults':len(ranked),
            'parent_rank':rank,'parent_percentile':((rank-1)/max(1,len(ranked)-1) if rank else None),
            'elite_parent':bool(rank and rank<=elite_slots),
            'parent_lifetime_mean_pct':(parent[2] if parent else None),'elite_slots':elite_slots}

def _inheritance_decision(m,ref):
    child=m.get('mean_return_pct'); baseline=ref.get('bloodline_baseline_pct'); parent_window=m.get('parent_window_mean_return_pct')
    absolute_viable=child is not None and child>0
    improvement=absolute_viable and baseline is not None and child >= baseline+BLOODLINE_IMPROVEMENT_MARGIN_PCT
    elite_parity=(absolute_viable and ref.get('elite_parent') and baseline is not None and parent_window is not None
                  and child>=baseline and child>=parent_window-ELITE_PARITY_TOLERANCE_PCT)
    return {'absolute_viable':absolute_viable,'improvement_path':bool(improvement),'elite_inheritance_path':bool(elite_parity),
            'passes_inheritance':bool(improvement or elite_parity),
            'parity_tolerance_pct':ELITE_PARITY_TOLERANCE_PCT,'improvement_margin_pct':BLOODLINE_IMPROVEMENT_MARGIN_PCT}

async def advance_lifecycle():
    await ensure_schema(); changes=[]
    async with connection() as c:
        scouts=await c.fetch("SELECT id,parent_genome_id,genome_id,genome,phenotype_id,state,created_at FROM colony_queen_scouts WHERE state IN ('nursery','paper') ORDER BY id")
        for s in scouts:
            m=await _metrics(c,s['id'],s['parent_genome_id']); age_h=(await c.fetchval("SELECT extract(epoch from (now()-$1))/3600",s['created_at'])) or 0
            g=s['genome'] if isinstance(s['genome'],dict) else json.loads(s['genome'])
            ref=await _bloodline_reference(c,g.get('family') or 'unknown',s['parent_genome_id'])
            inheritance=_inheritance_decision(m,ref)
            to_state=reason=None
            # Conservative negative-knowledge gate: only archive after enough independent
            # evidence, negative absolute expectancy, and material underperformance vs parent window.
            if (m['evidence_n']>=GRAVEYARD_MIN_EVIDENCE and m['parent_window_n']>=GRAVEYARD_MIN_PARENT_WINDOW
                and m['mean_return_pct'] is not None and m['mean_return_pct']<GRAVEYARD_BAD_ABSOLUTE_PCT
                and m['window_edge_vs_parent_pct'] is not None and m['window_edge_vs_parent_pct']<=GRAVEYARD_BAD_EDGE_PCT):
                to_state,reason='graveyard','evidence_backed_failure'
            elif s['state']=='nursery' and age_h>=NURSERY_MIN_HOURS and m['evidence_n']>=NURSERY_MIN_EVIDENCE and m['parent_window_n']>=NURSERY_MIN_CONTROLS:
                to_state,reason='paper','nursery_qc_pass'
            elif (s['state']=='paper' and age_h>=PAPER_MIN_HOURS and m['evidence_n']>=PAPER_MIN_EVIDENCE
                  and m['parent_window_n']>=PAPER_MIN_CONTROLS and inheritance['passes_inheritance']):
                path='elite_inheritance' if inheritance['elite_inheritance_path'] else 'bloodline_improvement'
                to_state,reason='live_ready',f'paper_validation_pass:{path}:live_still_disabled'
            if to_state:
                await c.execute("UPDATE colony_queen_scouts SET state=$2,stage_updated_at=now(),stage_reason=$3 WHERE id=$1",s['id'],to_state,reason)
                if to_state=='graveyard':
                    g=s['genome'] if isinstance(s['genome'],dict) else json.loads(s['genome'])
                    phid=s['phenotype_id'] or phenotype_id(g)
                    await c.execute('''INSERT INTO colony_genome_graveyard
                      (phenotype_id,genome_id,parent_genome_id,family,genome,reason,evidence_n,parent_window_n,mean_return_pct,edge_vs_parent_pct)
                      VALUES($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9,$10) ON CONFLICT(phenotype_id) DO NOTHING''',
                      phid,s['genome_id'],s['parent_genome_id'],g.get('family') or 'unknown',json.dumps(g),reason,
                      m['evidence_n'],m['parent_window_n'],m['mean_return_pct'],m['window_edge_vs_parent_pct'])
                await c.execute("INSERT INTO colony_queen_scout_lifecycle(scout_id,from_state,to_state,reason) VALUES($1,$2,$3,$4)",s['id'],s['state'],to_state,reason)
                changes.append({'scout_id':s['id'],'from':s['state'],'to':to_state,'reason':reason})
    return {'changes':changes,'live_execution_authority':False}
async def summary():
    await ensure_schema(); out=[]
    async with connection() as c:
        scouts=await c.fetch("SELECT id,genome_id,parent_genome_id,created_at,state,stage_reason,genome FROM colony_queen_scouts ORDER BY id DESC")
        for s in scouts:
            m=await _metrics(c,s['id'],s['parent_genome_id'])
            g=s['genome'] if isinstance(s['genome'],dict) else json.loads(s['genome'])
            ref=await _bloodline_reference(c,g.get('family') or 'unknown',s['parent_genome_id'])
            inheritance=_inheritance_decision(m,ref)
            out.append({'id':s['id'],'genome_id':s['genome_id'],'parent_genome_id':s['parent_genome_id'],
              'family':g.get('family'),'created_at':s['created_at'],'state':s['state'],'stage_reason':s['stage_reason'],**m,**ref,**inheritance})
    return out

async def lifecycle_history(limit=100):
    await ensure_schema()
    async with connection() as c:
        rows=await c.fetch('''SELECT l.scout_id,s.genome_id,s.genome->>'family' family,l.from_state,l.to_state,l.reason,l.created_at
          FROM colony_queen_scout_lifecycle l JOIN colony_queen_scouts s ON s.id=l.scout_id
          ORDER BY l.id DESC LIMIT $1''',limit)
    return [dict(r) for r in rows]

"""Queen-created shadow scouts. No population mutation, capital authority, signing or broadcast."""
import hashlib, json
from db import connection
from colony.genome import mutate, genome_id
from colony.forward import eligible

async def ensure_schema():
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_queen_scouts(
          id BIGSERIAL PRIMARY KEY,mind_experiment_id BIGINT NOT NULL,run_id TEXT NOT NULL,
          parent_genome_id TEXT NOT NULL,genome_id TEXT NOT NULL,genome JSONB NOT NULL,
          birth_cutoff BIGINT NOT NULL,created_at TIMESTAMPTZ DEFAULT now(),state TEXT NOT NULL DEFAULT 'shadow',
          UNIQUE(mind_experiment_id,genome_id))''')
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_queen_scout_entries(
          id BIGSERIAL PRIMARY KEY,scout_id BIGINT NOT NULL REFERENCES colony_queen_scouts(id),
          mint TEXT NOT NULL,candidate_id BIGINT NOT NULL,observed_at TIMESTAMPTZ NOT NULL,
          hold_minutes INTEGER NOT NULL,UNIQUE(scout_id,candidate_id))''')

async def active_count(family=None):
    await ensure_schema()
    async with connection() as c:
        if family:
            return int(await c.fetchval("SELECT count(*) FROM colony_queen_scouts WHERE state='shadow' AND genome->>'family'=$1",family))
        return int(await c.fetchval("SELECT count(*) FROM colony_queen_scouts WHERE state='shadow'"))

def _seed(experiment_id,parent_id,slot):
    return int(hashlib.sha256(f'queen:{experiment_id}:{parent_id}:{slot}'.encode()).hexdigest()[:8],16)
async def create(experiment_id,run_id,cutoff,parent_ids,max_scouts=2):
    await ensure_schema(); made=[]
    parent_ids=list(dict.fromkeys(parent_ids or []))[:max_scouts]
    async with connection() as c:
        families=[]
        for pid in parent_ids:
            row=await c.fetchrow("SELECT family FROM colony_genomes WHERE genome_id=$1 AND generation=3",pid)
            if row: families.append(row['family'])
        if not families: return {'created':0,'scouts':[],'mode':'shadow_only','why':'no_grounded_parents'}
        if len(set(families))!=1: return {'created':0,'scouts':[],'mode':'shadow_only','why':'one_bloodline_per_brood'}
        family=families[0]
        if await c.fetchval("SELECT count(*) FROM colony_queen_scouts WHERE state='shadow' AND genome->>'family'=$1",family) >= 4:
            return {'created':0,'scouts':[],'mode':'shadow_only','why':'bloodline_nursery_cap','family':family,'cap':4}
        for slot,pid in enumerate(parent_ids):
            row=await c.fetchrow("SELECT genome FROM colony_genomes WHERE genome_id=$1 AND generation=3",pid)
            if not row: continue
            parent=row['genome'] if isinstance(row['genome'],dict) else json.loads(row['genome'])
            child=mutate(parent,seed=_seed(experiment_id,pid,slot)); gid=genome_id(child)
            sid=await c.fetchval('''INSERT INTO colony_queen_scouts
              (mind_experiment_id,run_id,parent_genome_id,genome_id,genome,birth_cutoff)
              VALUES($1,$2,$3,$4,$5::jsonb,$6) ON CONFLICT DO NOTHING RETURNING id''',
              experiment_id,run_id,pid,gid,json.dumps(child),int(cutoff or 0))
            if sid: made.append({'scout_id':sid,'genome_id':gid,'parent':pid})
    return {'created':len(made),'scouts':made,'mode':'shadow_only'}

async def process():
    await ensure_schema(); inserted=0
    async with connection() as c:
        scouts=await c.fetch("SELECT id,genome,birth_cutoff FROM colony_queen_scouts WHERE state='shadow'")
        for s in scouts:
            g=s['genome'] if isinstance(s['genome'],dict) else json.loads(s['genome'])
            rows=await c.fetch("SELECT id,created_at,mint,features,market FROM research_candidates WHERE id>$1 ORDER BY id",s['birth_cutoff'])
            for row in rows:
                r=dict(row); prev=await c.fetchval("SELECT max(observed_at) FROM colony_queen_scout_entries WHERE scout_id=$1 AND mint=$2",s['id'],r['mint'])
                if not eligible(g,r,prev): continue
                hold=int(g.get('parameters',{}).get('hold_minutes',15))
                x=await c.execute('''INSERT INTO colony_queen_scout_entries
                  (scout_id,mint,candidate_id,observed_at,hold_minutes)
                  VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING''',s['id'],r['mint'],r['id'],r['created_at'],hold)
                inserted += int(x.endswith('1'))
    return {'scouts':len(scouts),'inserted':inserted}

async def summary():
    await ensure_schema(); out=[]
    async with connection() as c:
        scouts=await c.fetch("SELECT id,genome_id,parent_genome_id,created_at,state,birth_cutoff,genome FROM colony_queen_scouts ORDER BY id DESC")
        for s in scouts:
            child=await c.fetchrow('''SELECT count(DISTINCT e.mint) evidence_n,avg(o.net_return_pct) mean_return_pct
              FROM colony_queen_scout_entries e LEFT JOIN LATERAL
              (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=e.candidate_id AND measured_at>=e.observed_at
               ORDER BY abs(horizon_minutes-e.hold_minutes) LIMIT 1) o ON true WHERE e.scout_id=$1''',s['id'])
            control=await c.fetchrow('''SELECT count(*) control_n,avg(po.net_return_pct) parent_mean_return_pct
              FROM colony_queen_scout_entries ce
              JOIN colony_forward_entries pe ON pe.genome_id=$1 AND pe.candidate_id=ce.candidate_id
              LEFT JOIN LATERAL (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=pe.candidate_id
                AND measured_at>=pe.observed_at ORDER BY abs(horizon_minutes-pe.hold_minutes) LIMIT 1) po ON true
              WHERE ce.scout_id=$2''',s['parent_genome_id'],s['id'])
            cm=float(child['mean_return_pct']) if child['mean_return_pct'] is not None else None
            pm=float(control['parent_mean_return_pct']) if control['parent_mean_return_pct'] is not None else None
            g=s['genome'] if isinstance(s['genome'],dict) else json.loads(s['genome'])
            out.append({'id':s['id'],'genome_id':s['genome_id'],'parent_genome_id':s['parent_genome_id'],
              'family':g.get('family'),'created_at':s['created_at'],'state':s['state'],
              'evidence_n':int(child['evidence_n'] or 0),'mean_return_pct':cm,
              'control_n':int(control['control_n'] or 0),'parent_mean_return_pct':pm,
              'edge_vs_parent_pct':(cm-pm if cm is not None and pm is not None else None)})
    return out

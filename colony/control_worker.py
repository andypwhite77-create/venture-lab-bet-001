"""Feed identical prospective observations to frozen founder/blind controls."""
import json
from db import connection
from colony.forward import eligible, population_hash
from colony.genome import genome_id

async def ensure_controls(conn, source_run):
    from pathlib import Path
    root=Path(__file__).resolve().parent
    for kind,name in [('founders','control-founders.json'),('blind','control-blind.json')]:
        pop=json.loads((root/name).read_text()); cid=f"{source_run['run_id']}:{kind}"
        await conn.execute("""INSERT INTO colony_control_runs(control_id,kind,population_hash,population,started_at,frozen_until)
          VALUES($1,$2,$3,$4::jsonb,$5,$6) ON CONFLICT DO NOTHING""",
          cid,kind,population_hash(pop),json.dumps(pop),source_run['started_at'],source_run['frozen_until'])

async def process_controls():
    async with connection() as conn:
        source=await conn.fetchrow("SELECT * FROM colony_forward_runs WHERE status='collecting' ORDER BY started_at DESC LIMIT 1")
        if not source: return {'controls':0,'inserted':0}
        await ensure_controls(conn,source)
        controls=await conn.fetch("SELECT * FROM colony_control_runs WHERE started_at=$1 AND status='collecting'",source['started_at'])
        rows=await conn.fetch("SELECT id,created_at,mint,features,market FROM research_candidates WHERE created_at >= $1 ORDER BY id",source['started_at'])
        inserted=0
        for control in controls:
            pop=control['population']; pop=json.loads(pop) if isinstance(pop,str) else pop
            for row in rows:
                r=dict(row)
                for g in pop:
                    gid=genome_id(g); cd=int(g.get('parameters',{}).get('cooldown_minutes',0))
                    prev=await conn.fetchval("SELECT max(observed_at) FROM colony_control_entries WHERE control_id=$1 AND genome_id=$2 AND mint=$3",control['control_id'],gid,r['mint'])
                    if not eligible(g,r,prev): continue
                    hold=int(g.get('parameters',{}).get('hold_minutes',15))
                    res=await conn.execute("""INSERT INTO colony_control_entries
                      (control_id,genome_id,family,mint,candidate_id,observed_at,hold_minutes,cooldown_minutes)
                      VALUES($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT DO NOTHING""",
                      control['control_id'],gid,g['family'],r['mint'],r['id'],r['created_at'],hold,cd)
                    inserted += int(res.endswith('1'))
        return {'controls':len(controls),'candidates':len(rows),'inserted':inserted}

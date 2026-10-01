"""Prospective logger: feed new V1 candidates through the frozen colony."""
import asyncio, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'colony')]
from db import connection, init_db
from colony.forward import eligible
from colony.genome import genome_id

async def active_run(conn):
    # Forward collection is continuous. frozen_until was the original experiment
    # review horizon, not an expiry switch; treating it as expiry silently starved
    # prospective evidence after 48h.
    return await conn.fetchrow("""SELECT * FROM colony_forward_runs
      WHERE status='collecting' ORDER BY started_at DESC LIMIT 1""")

async def _progress(conn,key,run_id,entry_table,source_start):
    await conn.execute("CREATE TABLE IF NOT EXISTS colony_candidate_progress(stream_key TEXT PRIMARY KEY,last_candidate_id BIGINT NOT NULL DEFAULT 0,updated_at TIMESTAMPTZ NOT NULL DEFAULT now())")
    row=await conn.fetchrow('SELECT last_candidate_id FROM colony_candidate_progress WHERE stream_key=$1',key)
    if row:return int(row['last_candidate_id'])
    existing=await conn.fetchval(f'SELECT count(*) FROM {entry_table} WHERE run_id=$1',run_id)
    last=0
    if existing:
        last=int(await conn.fetchval('SELECT coalesce(max(id),0) FROM research_candidates WHERE created_at >= $1',source_start) or 0)
    await conn.execute('INSERT INTO colony_candidate_progress(stream_key,last_candidate_id) VALUES($1,$2) ON CONFLICT DO NOTHING',key,last)
    return last

async def process():
    async with connection() as conn:
        run=await active_run(conn)
        if not run: return {"run":None,"inserted":0}
        pop=run['population']; pop=json.loads(pop) if isinstance(pop,str) else pop
        key='forward:'+str(run['run_id'])
        last=await _progress(conn,key,run['run_id'],'colony_forward_entries',run['started_at'])
        rows=await conn.fetch("""SELECT id,created_at,mint,features,market FROM research_candidates
          WHERE created_at >= $1 AND id>$2 ORDER BY id""",run['started_at'],last)
        inserted=0
        for row in rows:
            r=dict(row)
            for g in pop:
                gid=genome_id(g); cooldown=int(g.get('parameters',{}).get('cooldown_minutes',0))
                prev=await conn.fetchval("SELECT max(observed_at) FROM colony_forward_entries WHERE run_id=$1 AND genome_id=$2 AND mint=$3",run['run_id'],gid,r['mint'])
                if not eligible(g,r,prev): continue
                hold=int(g.get('parameters',{}).get('hold_minutes',15))
                result=await conn.execute("""INSERT INTO colony_forward_entries
                  (run_id,genome_id,family,mint,candidate_id,observed_at,hold_minutes,cooldown_minutes)
                  VALUES($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT DO NOTHING""",
                  run['run_id'],gid,g['family'],r['mint'],r['id'],r['created_at'],hold,cooldown)
                inserted += int(result.endswith('1'))
        if rows:
            await conn.execute('UPDATE colony_candidate_progress SET last_candidate_id=$2,updated_at=now() WHERE stream_key=$1',key,rows[-1]['id'])
        return {"run":run['run_id'],"candidates":len(rows),"ants":len(pop),"inserted":inserted,"last_candidate_id":rows[-1]['id'] if rows else last}

async def main():
    await init_db()
    print(json.dumps(await process(),default=str))
if __name__=='__main__': asyncio.run(main())

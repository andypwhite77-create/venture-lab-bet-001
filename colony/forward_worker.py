"""Prospective logger: feed new V1 candidates through the frozen colony."""
import asyncio, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'colony')]
from db import connection, init_db
from colony.forward import eligible
from colony.genome import genome_id

async def active_run(conn):
    return await conn.fetchrow("""SELECT * FROM colony_forward_runs
      WHERE status='collecting' AND frozen_until > now() ORDER BY started_at DESC LIMIT 1""")

async def process():
    async with connection() as conn:
        run=await active_run(conn)
        if not run: return {"run":None,"inserted":0}
        pop=run['population']; pop=json.loads(pop) if isinstance(pop,str) else pop
        rows=await conn.fetch("""SELECT id,created_at,mint,features,market FROM research_candidates
          WHERE created_at >= $1 ORDER BY id""",run['started_at'])
        inserted=0
        for row in rows:
            r=dict(row)
            for g in pop:
                gid=genome_id(g); cooldown=int(g.get('parameters',{}).get('cooldown_minutes',0))
                prev=await conn.fetchval("""SELECT max(observed_at) FROM colony_forward_entries
                  WHERE run_id=$1 AND genome_id=$2 AND mint=$3""",run['run_id'],gid,r['mint'])
                if not eligible(g,r,prev): continue
                hold=int(g.get('parameters',{}).get('hold_minutes',15))
                result=await conn.execute("""INSERT INTO colony_forward_entries
                  (run_id,genome_id,family,mint,candidate_id,observed_at,hold_minutes,cooldown_minutes)
                  VALUES($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT DO NOTHING""",
                  run['run_id'],gid,g['family'],r['mint'],r['id'],r['created_at'],hold,cooldown)
                inserted += int(result.endswith('1'))
        return {"run":run['run_id'],"candidates":len(rows),"ants":len(pop),"inserted":inserted}

async def main():
    await init_db()
    print(json.dumps(await process(),default=str))
if __name__=='__main__': asyncio.run(main())

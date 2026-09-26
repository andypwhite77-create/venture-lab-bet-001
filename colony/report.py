"""Compact prospective colony report, including £25-equivalent paper balances."""
import asyncio, json
from db import init_db, connection
from colony.selection import ant_metrics

async def report():
    await init_db()
    async with connection() as conn:
        run=await conn.fetchrow("SELECT * FROM colony_forward_runs ORDER BY started_at DESC LIMIT 1")
        if not run: return {"status":"no_run"}
        rows=await conn.fetch("""SELECT e.genome_id,e.family,e.mint,e.hold_minutes,
          o.net_return_pct FROM colony_forward_entries e
          JOIN research_outcomes o ON o.candidate_id=e.candidate_id
          WHERE e.run_id=$1 AND o.horizon_minutes=(SELECT horizon_minutes FROM research_outcomes
            WHERE candidate_id=e.candidate_id ORDER BY abs(horizon_minutes-e.hold_minutes),horizon_minutes LIMIT 1)
          ORDER BY e.genome_id,e.observed_at""",run['run_id'])
        grouped={}
        for r in rows: grouped.setdefault((r['genome_id'],r['family']),[]).append((r['mint'],float(r['net_return_pct'])))
        ants=[]
        for (gid,fam),vals in grouped.items():
            m=ant_metrics(vals); unique={}
            for mint,ret in vals: unique.setdefault(mint,ret)
            balance=25.0
            for ret in unique.values(): balance*=1+ret/100
            ants.append({"genome_id":gid,"family":fam,"balance_25":round(balance,4),**m})
        ants.sort(key=lambda x:x['fitness'],reverse=True)
        return {"run_id":run['run_id'],"started_at":run['started_at'],"frozen_until":run['frozen_until'],
          "entries":len(rows),"scored_ants":len(ants),"independent_mints":len({r['mint'] for r in rows}),
          "top":ants[:10],"bottom":ants[-5:] if ants else []}

async def main(): print(json.dumps(await report(),indent=2,default=str))
if __name__=='__main__': asyncio.run(main())

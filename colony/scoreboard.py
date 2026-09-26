"""Fair prospective scoreboard: evolved vs founders vs blind mutants."""
import asyncio, json
from db import init_db, connection
from colony.selection import ant_metrics

async def score_entries(conn, table, key_col, key):
    rows=await conn.fetch(f"""SELECT e.genome_id,e.family,e.mint,e.hold_minutes,e.candidate_id,
      o.horizon_minutes,o.net_return_pct FROM {table} e JOIN LATERAL (
        SELECT horizon_minutes,net_return_pct FROM research_outcomes
        WHERE candidate_id=e.candidate_id ORDER BY abs(horizon_minutes-e.hold_minutes),horizon_minutes LIMIT 1
      ) o ON true WHERE e.{key_col}=$1""",key)
    grouped={}
    for r in rows: grouped.setdefault((r['genome_id'],r['family']),[]).append((r['mint'],float(r['net_return_pct'])))
    ants=[]
    for (gid,fam),vals in grouped.items():
        unique={}
        for mint,ret in vals: unique.setdefault(mint,ret)
        m=ant_metrics(list(unique.items())); bal=25.0
        for ret in unique.values(): bal*=1+ret/100
        ants.append({'genome_id':gid,'family':fam,'balance_25':bal,**m})
    return rows,ants

def summary(name,rows,ants,population_size):
    # Equal-capital convention: £25 allocated to every ant, including ants with no trades.
    balances={a['genome_id']:a['balance_25'] for a in ants}
    total=25.0*population_size + sum(v-25.0 for v in balances.values())
    return {'name':name,'population':population_size,'scored_ants':len(ants),
      'matured_entries':len(rows),'independent_mints':len({r['mint'] for r in rows}),
      'starting_capital':round(25*population_size,2),'paper_balance':round(total,2),
      'return_pct':round((total/(25*population_size)-1)*100,4),
      'best_ant':max(ants,key=lambda a:a['fitness']) if ants else None}

async def report():
    await init_db()
    async with connection() as conn:
        run=await conn.fetchrow("SELECT * FROM colony_forward_runs ORDER BY started_at DESC LIMIT 1")
        if not run:return {'status':'no_run'}
        erows,eants=await score_entries(conn,'colony_forward_entries','run_id',run['run_id'])
        out=[summary('evolved_gen3',erows,eants,len(json.loads(run['population']) if isinstance(run['population'],str) else run['population']))]
        controls=await conn.fetch("SELECT * FROM colony_control_runs WHERE started_at=$1 ORDER BY kind",run['started_at'])
        for c in controls:
            rows,ants=await score_entries(conn,'colony_control_entries','control_id',c['control_id'])
            out.append(summary(c['kind'],rows,ants,len(json.loads(c['population']) if isinstance(c['population'],str) else c['population'])))
        return {'run_id':run['run_id'],'started_at':run['started_at'],'frozen_until':run['frozen_until'],'groups':out}

async def main(): print(json.dumps(await report(),indent=2,default=str))
if __name__=='__main__': asyncio.run(main())

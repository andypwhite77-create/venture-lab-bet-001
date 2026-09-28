import asyncio,json
from db import init_db,connection
from colony.reversal_tournament import metrics, rank_with_correlation
async def report():
 await init_db()
 async with connection() as c:
  run=await c.fetchrow("SELECT * FROM reversal_tournament_runs ORDER BY created_at DESC LIMIT 1")
  if not run:return {"status":"no_run"}
  recs=await metrics(c,run['run_id']); ranked=rank_with_correlation(recs)
  active=await c.fetch("SELECT genome_id FROM reversal_tournament_ants WHERE run_id=$1 AND active=true",run['run_id'])
  active_ids={r['genome_id'] for r in active}
  def clean(gid,r):return {'genome_id':gid,**{k:v for k,v in r.items() if k!='mints'}}
  return {'run_id':run['run_id'],'status':run['status'],'stage_size':run['stage_size'],'stage_index':run['stage_index'],
          'active_ants':len(active_ids),'scored_ants':len(recs),'top':[clean(g,r) for g,r in ranked if g in active_ids][:10]}
async def main():print(json.dumps(await report(),indent=2,default=str))
if __name__=='__main__':asyncio.run(main())

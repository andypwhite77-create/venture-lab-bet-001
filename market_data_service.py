"""Dedicated, non-executing market data collection daemon."""
import asyncio,json,logging
from db import init_db,connection
from research_db import ensure_research_schema
from path_sampler import sample_active_paths
logging.basicConfig(level=logging.INFO)
log=logging.getLogger('venture-lab.market-data')
async def archive_recent():
 async with connection() as c:
  return await c.execute("""INSERT INTO market_price_history
    (mint,collected_at,price,provider,quality,source_observed_at,source_path_id)
    SELECT DISTINCT ON (r.mint,date_trunc('minute',p.observed_at))
      r.mint,p.observed_at,p.price,p.provider,p.quality,p.source_observed_at,p.id
    FROM research_price_path p JOIN research_candidates r ON r.id=p.candidate_id
    WHERE p.observed_at>now()-interval '6 minutes' AND p.quality='fresh_fetch'
    AND p.provider IS NOT NULL
    ORDER BY r.mint,date_trunc('minute',p.observed_at),p.observed_at DESC,p.id DESC
    ON CONFLICT(source_path_id) DO NOTHING""")
async def main():
 await init_db();await ensure_research_schema()
 while True:
  try:
   result=await sample_active_paths()
   archived=await archive_recent()
   result["history_archive"]=archived
   async with connection() as c:
    await c.execute("INSERT INTO market_data_cycles(active,recorded,missing,coverage_ratio,details) VALUES($1,$2,$3,$4,$5::jsonb)",result['active'],result['recorded'],result['missing'],result['coverage_ratio'],json.dumps(result))
   log.info('price_cycle %s',json.dumps(result))
  except Exception:
   log.exception('price_cycle_failed')
  await asyncio.sleep(60)
if __name__=='__main__':asyncio.run(main())

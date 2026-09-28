import asyncio,json
from db import init_db,connection
from colony.surrogate_breeder import run_all
from colony.pattern_discovery import discover
from colony.continuous_evolution import seed_queue_from_latest_nursery
async def main():
 await init_db()
 async with connection() as c:
  print('GUIDED',json.dumps(await run_all(c),default=str),flush=True)
  p=await discover(c,30)
  for x in p['top']:
   await c.execute('INSERT INTO discovered_patterns(rule,robust_score,evidence) VALUES($1::jsonb,$2,$3::jsonb)',json.dumps(x['rule']),x['robust_score'],json.dumps(x,default=str))
  print('PATTERNS',json.dumps({'tested':p['tested_rules'],'qualified':p['qualified'],'positive_robust':p['positive_robust'],'top':p['top'][:5]},default=str),flush=True)
  print('QUEUE',json.dumps(await seed_queue_from_latest_nursery(c),default=str),flush=True)
asyncio.run(main())

"""Four-family, bounded autonomous research round. Historical research only.
Each family makes one proposal. Durable records and the existing duplicate gate apply.
"""
import asyncio,json,datetime
from db import init_db,connection
from colony.queen_historical_autoresearch import QUEENS
from colony.queen_pair_autoresearch import propose

SCHEMA='''CREATE TABLE IF NOT EXISTS queen_research_batch_runs
(id bigserial primary key, started_at timestamptz not null default clock_timestamp(),
 completed_at timestamptz, status text not null, result jsonb);'''

async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  await c.execute('SELECT pg_advisory_xact_lock(917204)')
  last=await c.fetchval('SELECT started_at FROM queen_research_batch_runs ORDER BY id DESC LIMIT 1')
  if last and (await c.fetchval('SELECT clock_timestamp()'))-last < datetime.timedelta(minutes=50):
   return {'status':'cooldown','promotion_allowed':False}
  run_id=await c.fetchval("INSERT INTO queen_research_batch_runs(status) VALUES('running') RETURNING id")
 results=[]
 for queen in QUEENS:
  try:
   result=await propose(queen)
   results.append({'queen':queen,'status':result.get('status'),'pair_key':result.get('pair_key'),'evidence':result.get('result',{}).get('result',{}).get('status')})
  except Exception as ex:
   results.append({'queen':queen,'status':'error','error':type(ex).__name__})
 report={'status':'complete','results':results,'promotion_allowed':False,'live_trading_allowed':False,'breeding_allowed':False}
 async with connection() as c:
  await c.execute('UPDATE queen_research_batch_runs SET completed_at=clock_timestamp(),status=$2,result=$3::jsonb WHERE id=$1',run_id,'complete',json.dumps(report))
 return report
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str))

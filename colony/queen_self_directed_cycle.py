"""Autonomous, bounded read-only Queen research prioritised by paper loss evidence.
One eligible family per daily cycle. Nothing can promote, breed, or trade.
"""
import asyncio,json
from db import init_db,connection
from colony.queen_research_objectives import family_objective
from colony.queen_pair_autoresearch import propose
from colony.queen_historical_autoresearch import QUEENS
SCHEMA='''CREATE TABLE IF NOT EXISTS queen_self_directed_cycles(id bigserial primary key, queen text not null, started_at timestamptz not null default clock_timestamp(), status text not null, result jsonb);'''
def choose(rows):
 eligible=[]
 for r in rows:
  queen=r['queen'];data=r.get('feedback')
  if queen not in QUEENS or not data:continue
  priority=data.get('research_priorities',[])
  if not priority:continue
  loss=abs(min(0,float(data.get('hypothetical_net_sol',0))))
  locked=float(data.get('locked_sol',0))
  eligible.append((loss+locked*.25,queen))
 return sorted(eligible,reverse=True)[0][1] if eligible else None
async def run():
 await init_db()
 rows=[]
 for q in QUEENS:rows.append({'queen':q,'feedback':(await family_objective(q))['feedback']})
 async with connection() as c:
  await c.execute(SCHEMA)
  last=await c.fetchval("SELECT started_at FROM queen_self_directed_cycles ORDER BY id DESC LIMIT 1")
  if last and (await c.fetchval('SELECT clock_timestamp()'))-last < __import__('datetime').timedelta(hours=2):return {'status':'research_cooldown','promotion_allowed':False}
  recent=await c.fetch('SELECT queen,count(*) AS n FROM (SELECT queen FROM queen_self_directed_cycles ORDER BY id DESC LIMIT 8) x GROUP BY queen')
  counts={r['queen']:r['n'] for r in recent}
  candidates=[r for r in rows if r['queen'] in QUEENS and r.get('feedback') and r['feedback'].get('research_priorities')]
  queen=min((r['queen'] for r in candidates),key=lambda q:(counts.get(q,0),q)) if candidates else None
  if not queen:return {'status':'no_supported_priority','promotion_allowed':False}
  rec=await c.fetchval("INSERT INTO queen_self_directed_cycles(queen,status) VALUES($1,'running') RETURNING id",queen)
 try:out=await propose(queen);status=out['status']
 except Exception as ex:out={'error':type(ex).__name__};status='failed'
 async with connection() as c:
  await c.execute('UPDATE queen_self_directed_cycles SET status=$2,result=$3::jsonb WHERE id=$1',rec,status,json.dumps(out,default=str))
 return {'queen':queen,'status':status,'result':out,'promotion_allowed':False,'live_trading_allowed':False}
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str))

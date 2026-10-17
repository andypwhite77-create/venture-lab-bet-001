"""Read-only ETH paper performance and conservative per-arm capital accounting."""
import asyncio,json
from collections import defaultdict
from db import init_db,connection
SCHEMA='''CREATE TABLE IF NOT EXISTS eth_queen_scoreboard_history(id bigserial PRIMARY KEY, recorded_at timestamptz NOT NULL DEFAULT now(), report jsonb NOT NULL);'''
def assess(rows):
 grouped=defaultdict(list)
 for r in rows:grouped[r['strategy']].append(dict(r))
 result={}
 for name,items in grouped.items():
  realized=sum(float(r['net_pnl_usd']) for r in items if r['status']=='closed' and r['net_pnl_usd'] is not None)
  completed=sum(r['status']=='closed' and r['net_pnl_usd'] is not None for r in items)
  open_count=sum(r['status']=='open' for r in items)
  equity=125+realized;cash=equity-25*open_count
  result[name]={'completed':completed,'open':open_count,'closed_net_usd':round(realized,4),'book_equity_usd':round(equity,4),'available_cash_usd':round(cash,4),'capital_constraint_breached':cash<0,'research_status':'insufficient_evidence' if completed<25 else 'underwater' if realized<=0 else 'provisional_positive'}
 return {'market':'ETH/USD','arms':result,'starting_cash_usd_per_arm':125,'stake_usd':25,'authority':'paper_only','warning':'OHLC mark-to-market proxy, not executable fills; no live promotion.'}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  rows=await c.fetch('SELECT strategy,status,net_pnl_usd FROM eth_queen_paper')
  result=assess(rows)
  await c.execute('INSERT INTO eth_queen_scoreboard_history(report) VALUES($1::jsonb)',json.dumps(result))
 return result
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

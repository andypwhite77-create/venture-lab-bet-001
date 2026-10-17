"""Read-only survival pressure scoreboard: urgency means evidence-backed improvement."""
import asyncio,json
from datetime import datetime,timezone
from db import init_db,connection
from colony.shared_wallet_shadow import SQL,simulate

SCHEMA='''CREATE TABLE IF NOT EXISTS queen_profit_pressure_runs (
 id bigserial primary key, assessed_at timestamptz not null default now(),
 report jsonb not null, authority text not null default 'research_only');'''

def assess(records,as_of=None):
 now=as_of or datetime.now(timezone.utc)
 # Study is deliberately frozen at the first clean wallet start, and is
 # evaluated identically every time. Never reset losses to manufacture success.
 start=datetime.fromisoformat('2026-10-16T21:16:08+00:00')
 cohort=[r for r in records if r['entry_at']>=start]
 wallet=simulate(cohort,as_of=now)
 policies={}
 for name,m in wallet['results'].items():
  pnl=m['closed_pnl_gbp'];unresolved=m['unresolved'];counts=m['counts']
  policies[name]={'net_mark_pnl_gbp':pnl,'book_equity_gbp':m['book_equity_gbp'],
   'free_cash_gbp':m['cash_gbp'],'locked_gbp':m['locked_gbp'],
   'overdue_positions':unresolved['overdue'],'completed_marks':counts.get('marked',0),
   'survival_status':'capital_stranded' if m['cash_gbp']<=0 else 'underwater' if pnl<0 else 'unproven_positive',
   'required_research':'restore valid exit evidence and recycle capital' if unresolved['overdue'] else 'find lower-tail, net-positive strategies without raising exposure'}
 return {'evaluated_at':now.isoformat(),'cohort_start':start.isoformat(),
  'policies':policies,'objective':'maximize repeatable capital-limited net surplus with cash recycling and independently verified execution',
  'urgency':'new proposals must quantify expected uplift, downside tail, funding required and falsification criterion',
  'no_shortcut':'no higher leverage, fabricated close, Spartan threshold tuning, live promotion, auto-breeding or market manipulation',
  'authority':'read_only_diagnostic_no_execution'}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  rows=await c.fetch(SQL)
  report=assess(rows)
  await c.execute('INSERT INTO queen_profit_pressure_runs(report) VALUES($1::jsonb)',json.dumps(report))
 return report
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

"""Frozen, prospective net-profit survival floor; no authority over Spartan/live.

This scoreboard cannot declare a winner from unpriced open positions or a small
profitable streak. It never deletes genomes, changes exam rules, or trades.
"""
import asyncio,json
from datetime import datetime,timezone
from db import init_db,connection
from colony.queen_profit_pressure import assess
from colony.shared_wallet_shadow import SQL

SCHEMA='''CREATE TABLE IF NOT EXISTS queen_survival_floor_snapshots (
 id bigserial primary key, evaluated_at timestamptz not null default now(),
 report jsonb not null, authority text not null default 'research_only');'''

# Conservative initial *research* qualification; not an assertion of live edge.
MIN_CLOSED_MARKS=25
MIN_DISTINCT_DAYS=7
MIN_NET_PROFIT_GBP=1.0
MIN_END_EQUITY_GBP=126.0

def rank_policy(report, days):
 p=report['policies'];results={}
 for name,v in p.items():
  n=int(v['completed_marks']); pnl=float(v['net_mark_pnl_gbp'])
  equity=float(v['book_equity_gbp']);overdue=v['overdue_positions']
  blockers=[]
  if n<MIN_CLOSED_MARKS:blockers.append('insufficient_closed_marks')
  if days<MIN_DISTINCT_DAYS:blockers.append('insufficient_distinct_days')
  if pnl<MIN_NET_PROFIT_GBP:blockers.append('non_positive_surplus_after_assumed_costs')
  if equity<MIN_END_EQUITY_GBP:blockers.append('capital_below_research_floor')
  if overdue:blockers.append('overdue_unresolved_positions')
  results[name]={'research_floor_candidate':not blockers,'blockers':blockers,
   'closed_marks':n,'net_mark_pnl_gbp':pnl,'book_equity_gbp':equity}
 return results

def decide(report,days):
 ranked=rank_policy(report,days)
 passed=[name for name,r in ranked.items() if r['research_floor_candidate']]
 return {'policy_assessments':ranked,'would_freeze_research_floor':passed,
  'floor_active':False,'why':'Requires separate independent prospective evidence and explicit approval before freezing an immutable champion benchmark',
  'culling_rule':'Archive failed hypotheses, annotate reasons; exclude from promotion shortlist only, never delete evidence',
  'spartan':'Sealed independent examination unchanged','live':'No allocation, arming or auto-promotion'}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  records=await c.fetch(SQL)
  status=assess(records)
  start=datetime.fromisoformat(status['cohort_start'])
  # Only days with actually observed prospective entries count.
  days=len({r['entry_at'].date() for r in records if r['entry_at']>=start})
  report={'survival':status,'minimum_research_floor':{'completed_marks':MIN_CLOSED_MARKS,'observed_days':MIN_DISTINCT_DAYS,'net_mark_profit_gbp':MIN_NET_PROFIT_GBP,'book_equity_gbp':MIN_END_EQUITY_GBP},
          'decision':decide(status,days),'distinct_observation_days':days}
  await c.execute('INSERT INTO queen_survival_floor_snapshots(report) VALUES($1::jsonb)',json.dumps(report))
 return report
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

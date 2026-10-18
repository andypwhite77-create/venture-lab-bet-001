"""Research-only scoreboard over accepted post-activation quote-derived cash events.
Unrealized positions stay locked; results are NOT fills or annualized returns.
"""
import asyncio,json
from collections import defaultdict
from datetime import datetime,timezone
from db import init_db,connection
from colony.capital_reconciliation import START_LAMPORTS

def score(rows,as_of,starting=START_LAMPORTS):
 groups=defaultdict(list)
 for item in rows:groups[str(item['genome_id'])].append(dict(item))
 results={}
 for gid,events in groups.items():
  cash=starting;open_positions={};completed=0;rejected=0;net=0;peak=starting;max_drawdown=0;capital_seconds=0;last=None
  for e in sorted(events,key=lambda x:(x['decided_at'],x['source_event_id'])):
   t=e['decided_at']
   if last is not None:capital_seconds+=sum(open_positions.values())*max(0,(t-last).total_seconds())
   last=t
   if not e['accepted']:rejected+=1;continue
   key=e['source_entry_id'];amount=int(e['amount_lamports'])
   if e['action']=='reserve':
    if key in open_positions or amount>cash:raise ValueError('funded reservation replay mismatch')
    cash-=amount;open_positions[key]=amount
   elif e['action']=='release':
    if key not in open_positions:raise ValueError('unfunded release in accepted events')
    original=open_positions.pop(key);cash+=amount;net+=amount-original;completed+=1
    equity=cash+sum(open_positions.values());peak=max(peak,equity)
    max_drawdown=max(max_drawdown,peak-equity)
   else:raise ValueError('unknown accepted action')
  if last is not None:capital_seconds+=sum(open_positions.values())*max(0,(as_of-last).total_seconds())
  locked=sum(open_positions.values());equity=cash+locked
  results[gid]={'completed_quote_round_trips':completed,'pending_positions':len(open_positions),'available_sol':round(cash/1e9,9),'locked_sol':round(locked/1e9,9),'realized_hypothetical_net_sol':round(net/1e9,9),'hypothetical_equity_excluding_unrealized_marks_sol':round(equity/1e9,9),'rejected_events':rejected,'locked_capital_sol_hours':round(capital_seconds/3.6e12,8),'realized_drawdown_sol':round(max_drawdown/1e9,9),'eligible_for_comparison':bool(completed>=25 and not open_positions and rejected==0)}
 return results
async def run():
 await init_db()
 async with connection() as c:
  rows=await c.fetch('''SELECT source_event_id,genome_id,source_entry_id,action,amount_lamports,accepted,decided_at FROM funded_paper_event_decisions ORDER BY source_event_id''')
  data=score(rows,datetime.now(timezone.utc))
 return {'genomes':data,'authority':'research_only_quote_evidence_not_fills','limitations':'locked capital valued at cost; no executable fills or unrealized marks; cannot qualify alone'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

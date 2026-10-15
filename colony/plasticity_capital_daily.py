"""Read-only bankroll-limited comparison; outcome marks are NOT executable fills."""
import asyncio,json,heapq
from collections import defaultdict
from datetime import timezone
from db import init_db,connection
QUERY="""SELECT e.id entry_id,e.genome_id,e.observed_at entry_at,e.stake_gbp,d.action,
 l.outcome_at,l.captured_at,l.net_return_pct
 FROM plasticity_forward_decisions d JOIN eve_reference_paper_entries e ON e.id=d.entry_id
 LEFT JOIN controlled_paper_trade_ledger l ON l.entry_id=e.id
 ORDER BY e.genome_id,e.observed_at,e.id"""
def replay(rows,initial_gbp=25,extra_friction_pct=1):
 if initial_gbp<=0 or extra_friction_pct<0:raise ValueError('invalid capital assumptions')
 by=defaultdict(list)
 for raw in rows:
  r=dict(raw);by[r['genome_id']].append(r)
 result={}
 for arm in ('fixed_dna','plasticity'):
  days=defaultdict(float);per=[]
  for genome,entries in by.items():
   cash=float(initial_gbp);locked=0.;openq=[];skipped=0;abstained=0;trades=0
   def close_due(at):
    nonlocal cash,locked
    while openq and openq[0][0]<=at:
     _,_,stake,pnl=heapq.heappop(openq);locked-=stake;cash+=stake+pnl
   for row in sorted(entries,key=lambda v:(v['entry_at'],v['entry_id'])):
    close_due(row['entry_at'])
    if arm=='plasticity' and row['action']!='follow_dna':abstained+=1;continue
    stake=min(cash,initial_gbp,float(row['stake_gbp']))
    if stake<=0:skipped+=1;continue
    cash-=stake;locked+=stake
    if row['net_return_pct'] is None or row['outcome_at'] is None or row['captured_at'] is None:
     continue # Missing outcome leaves stake locked, never credited as profit.
    closing=max(row['outcome_at'],row['captured_at'],row['entry_at'])
    pnl=max(-stake,stake*(float(row['net_return_pct'])-extra_friction_pct)/100)
    heapq.heappush(openq,(closing,row['entry_id'],stake,pnl));trades+=1
    days[closing.astimezone(timezone.utc).date().isoformat()]+=pnl
   close_due(max((x[0] for x in openq),default=entries[-1]['entry_at']))
   per.append({'genome_id':genome,'cash_gbp':round(cash,3),'locked_unmarked_gbp':round(locked,3),
    'completed':trades,'no_cash':skipped,'abstained':abstained})
  result[arm]={'per_genome':per,'daily_pnl_gbp':{k:round(v,3) for k,v in sorted(days.items())},
   'profitable_days':sum(v>0 for v in days.values()),'losing_days':sum(v<0 for v in days.values()),
   'total_closed_pnl_gbp':round(sum(days.values()),3),'worst_day_gbp':round(min(days.values()),3) if days else None}
 return {'initial_gbp_per_genome':initial_gbp,'extra_friction_pct':extra_friction_pct,'arms':result,
  'limitation':'Indicative historical marks with captured_at close; not executable, no live trading authority.'}
async def run():
 await init_db()
 async with connection() as c:rows=await c.fetch(QUERY)
 return replay(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

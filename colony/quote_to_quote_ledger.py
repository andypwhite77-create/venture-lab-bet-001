"""Conservative read-only SOL quote-to-quote evidence and per-genome cash ledger.
No transaction execution. Missing/late quotes are not profit. Each genome gets its
own hypothetical 0.1 SOL and independently reserves 0.01 SOL per position.
"""
import asyncio,json
from collections import defaultdict
from db import init_db,connection
SCHEMA='''CREATE TABLE IF NOT EXISTS quote_to_quote_reviews(id bigserial PRIMARY KEY,reviewed_at timestamptz NOT NULL DEFAULT now(),report jsonb NOT NULL);'''
START_SOL=0.1
EXTRA_EXIT_FRICTION=0.002
MAX_DELAY_SECONDS=120

def valid(row,phase):
 q=row.get(phase+'_quote')
 if isinstance(q,str):
  try:q=json.loads(q)
  except ValueError:return None
 if row.get(phase+'_status')!='quoted' or not isinstance(q,dict):return None
 lag=row.get(phase+'_latency')
 if lag is None or not 0<=float(lag)<=MAX_DELAY_SECONDS:return None
 try:
  incoming=int(q['in_amount']);outgoing=int(q['out_amount'])
  if incoming<=0 or outgoing<=0 or not q.get('route_labels'):return None
  return incoming,outgoing
 except (ValueError,TypeError,KeyError):return None

def assess(rows):
 books=defaultdict(list)
 for r in rows:books[str(r['genome_id'])].append(dict(r))
 results={}
 for genome,records in books.items():
  cash=START_SOL;active=[];complete=unverified=blocked=0;net=stress=0.
  for r in sorted(records,key=lambda x:(x['observed_at'],x['id'])):
   # Cash cannot be reused until the earlier position's scheduled exit.
   current=r['observed_at'];releasable=[p for p in active if p[0]<=current]
   for _,returned in releasable:cash+=returned
   active=[p for p in active if p[0]>current]
   entry=valid(r,'entry');exit_=valid(r,'exit')
   if not entry:unverified+=1;continue
   stake=entry[0]/1e9
   if cash+1e-12<stake:blocked+=1;continue
   cash-=stake
   if not exit_ or exit_[0]!=entry[1]:unverified+=1;continue # unresolved: capital remains locked
   proceeds=exit_[1]/1e9
   pnl=proceeds-stake;net+=pnl;stress+=pnl-stake*EXTRA_EXIT_FRICTION
   active.append((r['exit_due'],proceeds));complete+=1
  for _,returned in active:cash+=returned
  results[genome]={'quote_pairs':complete,'missing_or_invalid_pairs':unverified,'blocked_by_simulated_cash':blocked,'net_quote_sol':round(net,9),'stressed_net_sol':round(stress,9),'available_book_cash_sol':round(cash,9),'unresolved_reserved_sol':round(max(0,START_SOL+net-cash),9),'capital_basis_sol':START_SOL}
 return {'genomes':results,'evidence':'sized prospective Jupiter quotes, not fills','limitations':'0.01 SOL reference stake, independent simulated genome bankrolls; fees, congestion, liquidity changes and real execution may differ','authority':'research_only_no_orders'}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  rows=await c.fetch('''SELECT e.id,e.genome_id,e.observed_at,e.observed_at+e.hold_minutes*interval '1 minute' exit_due,
    a.quote entry_quote,a.status entry_status,a.latency_seconds entry_latency,
    x.quote exit_quote,x.status exit_status,x.latency_seconds exit_latency
    FROM eve_reference_paper_entries e
    JOIN controlled_paper_cohort cc ON cc.genome_id=e.genome_id AND cc.status='observation_only' AND e.observed_at>=cc.started_at
    LEFT JOIN canary_forward_quote_observations a ON a.entry_id=e.id AND a.phase='entry'
    LEFT JOIN canary_forward_quote_observations x ON x.entry_id=e.id AND x.phase='exit'
    ORDER BY e.genome_id,e.observed_at,e.id''')
  report=assess(rows)
  await c.execute('INSERT INTO quote_to_quote_reviews(report) VALUES($1::jsonb)',json.dumps(report))
 return report
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

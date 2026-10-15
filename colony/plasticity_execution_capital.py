"""Execution-evidence-aware £25 shadow capital stress test; no fills assumed."""
import asyncio,json
from collections import Counter,defaultdict
from db import init_db,connection
from colony.plasticity_capital_daily import QUERY,replay
from colony.plasticity_execution_review import classify

SQL=QUERY.replace(' l.outcome_at,l.captured_at,l.net_return_pct',' l.outcome_at,l.captured_at,l.net_return_pct,\n a.status entry_status,a.latency_seconds entry_latency,\n b.status exit_status,b.latency_seconds exit_latency').replace(' LEFT JOIN controlled_paper_trade_ledger l ON l.entry_id=e.id',' LEFT JOIN controlled_paper_trade_ledger l ON l.entry_id=e.id\n LEFT JOIN canary_forward_quote_observations a ON a.entry_id=e.id AND a.phase=\'entry\'\n LEFT JOIN canary_forward_quote_observations b ON b.entry_id=e.id AND b.phase=\'exit\'')

def compare(rows):
 records=[dict(r) for r in rows]
 diagnostic=replay(records)
 counts=Counter(classify(r) for r in records)
 # Strict stress scenario: only timely paired quotes can credit a profitable
 # close. Missing/delayed quote positions remain capital-locked. This is NOT
 # an estimate of realised loss or realistic eventual liquidation recovery.
 strict=[]
 for row in records:
  x=dict(row)
  if classify(x)!='timely_pair_not_fill':
   x['outcome_at']=None;x['captured_at']=None;x['net_return_pct']=None
  strict.append(x)
 return {'diagnostic_mark_model':diagnostic,'timely_quote_only_stress':replay(strict),
         'evidence_counts':dict(counts),'authority':'research_only_no_live',
         'caution':'Quote-qualified returns still use sampled market marks, NOT Jupiter net fills; unverified positions stay locked in the strict stress case.'}
async def run():
 await init_db()
 async with connection() as c:rows=await c.fetch(SQL)
 return compare(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

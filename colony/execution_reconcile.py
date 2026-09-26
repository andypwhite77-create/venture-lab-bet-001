"""Reconcile accepted simulated executions against later marks."""
from db import connection
from colony.execution_ledger import mark
async def pending(run_id=None,limit=100):
 async with connection() as c:
  if run_id:
   rows=await c.fetch("SELECT intent_id,mint,side,notional,quote,created_at FROM colony_execution_ledger WHERE status='accepted' AND mark_price IS NULL AND run_id=$1 ORDER BY id LIMIT $2",run_id,limit)
  else:
   rows=await c.fetch("SELECT intent_id,mint,side,notional,quote,created_at FROM colony_execution_ledger WHERE status='accepted' AND mark_price IS NULL ORDER BY id LIMIT $1",limit)
 return [dict(r) for r in rows]
def friction(notional,slippage_bps=0,network_cost=0.0):
 return float(notional)*float(slippage_bps)/10000.0+float(network_cost)
async def reconcile(intent_id,entry_price,mark_price,slippage_bps=0,network_cost=0.0):
 async with connection() as c:r=await c.fetchrow('SELECT notional FROM colony_execution_ledger WHERE intent_id=$1',intent_id)
 if not r:return None
 cost=friction(r['notional'],slippage_bps,network_cost)
 return await mark(intent_id,entry_price,mark_price,cost)

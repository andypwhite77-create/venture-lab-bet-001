"""Executor state is derived from ledger, not colony self-report."""
from db import connection
async def state(run_id=None):
 async with connection() as c:
  where='WHERE run_id=$1' if run_id else '';args=[run_id] if run_id else []
  r=await c.fetchrow(f'''SELECT coalesce(sum(net_pnl),0) daily_pnl,
   coalesce(sum(notional) FILTER(WHERE status='accepted' AND mark_price IS NULL),0) open_notional,
   array_agg(intent_id) FILTER(WHERE intent_id IS NOT NULL) seen_ids
   FROM colony_execution_ledger {where}''',*args)
  return {'daily_pnl':float(r['daily_pnl'] or 0),'open_notional':float(r['open_notional'] or 0),'seen_ids':set(r['seen_ids'] or [])}

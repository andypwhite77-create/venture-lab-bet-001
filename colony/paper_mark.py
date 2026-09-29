"""Mark simulated entries from independent live price providers."""
import asyncio
from colony.sensors import snapshot
from colony.execution_reconcile import pending,reconcile
from colony.execution_reality import roundtrip
from colony.execution_ledger import record_reality
from colony.paper_economics import measured_roundtrip_network_fee_sol,economics,sol_gbp_rate
from db import connection
async def _price(mint):
 s=await snapshot(mint)
 vals=[float(x['price_usd']) for x in s['sources'] if x.get('ok') and x.get('price_usd')]
 return (sum(vals)/len(vals) if vals else None),s
async def mark_pending(run_id='paper-livequote-v1',slippage_bps=100):
 rows=await pending(run_id,200);out=[]
 async with connection() as c:
  network_floor=await measured_roundtrip_network_fee_sol(c)
 rate,_rate_source=sol_gbp_rate()
 for r in rows:
  q=r.get('quote') or {}
  if isinstance(q,str):
   import json;q=json.loads(q)
  entry=float(q.get('signal_reference_price') or 0)
  if entry<=0:continue
  # Respect the strategy hold before marking; never score an ant at daemon-cycle time.
  attr=q.get('attribution') or {}
  hold_minutes=int(attr.get('hold_minutes') or 15)
  created=r.get('created_at')
  if created:
   from datetime import datetime,timezone,timedelta
   now=datetime.now(timezone.utc)
   if created + timedelta(minutes=hold_minutes) > now: continue
  price,sources=await _price(r['mint'])
  reality=roundtrip(r['mint'],q,float(r['notional']))
  # Accounting authority is executable SOL round-trip economics, not provider token
  # spot prices. Tiny-token provider prices can differ by units/decimals/pools and
  # previously created impossible multi-SOL P&L on a ~0.28 SOL stake.
  if reality.get('ok'):
   gross=float(reality['gross_edge_sol'])
   friction_cost=float(r['notional'])*slippage_bps/10000.0+network_floor
   mark_price=entry*(1.0+gross/float(r['notional']))
   pnl=await reconcile(r['intent_id'],entry,mark_price,slippage_bps,network_floor)
  elif price:
   # Provider mark is retained only as a degraded fallback when executable quotes fail.
   pnl=await reconcile(r['intent_id'],entry,price,slippage_bps,network_floor)
  else:
   continue
  gross_pct=(float(pnl.get('gross_pnl') or 0)/float(r['notional'])*100.0) if pnl and float(r['notional']) else 0.0
  stake_gbp=float(r['notional'])*rate
  econ=economics(gross_pct,stake_gbp=stake_gbp,fixed_cost_gbp=network_floor*rate,proportional_cost_pct=slippage_bps/100.0)
  reality['stake_economics']=econ; reality['measured_roundtrip_network_fee_sol']=network_floor; reality['sol_gbp_rate']=rate; reality['rate_source']=_rate_source
  await record_reality(r['intent_id'],reality,(pnl or {}).get('friction_cost',0.0))
  out.append({'intent_id':r['intent_id'],'entry_price':entry,'mark_price':price,'pnl':pnl,'execution_reality':reality,'sources':sources['source_count']})
  await asyncio.sleep(.15)
 return out

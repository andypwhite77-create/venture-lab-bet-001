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
  price,sources=await _price(r['mint'])
  if not price:continue
  reality=roundtrip(r['mint'],q,float(r['notional']))
  pnl=await reconcile(r['intent_id'],entry,price,slippage_bps,network_floor)
  gross_pct=(float(pnl.get('gross_pnl') or 0)/float(r['notional'])*100.0) if pnl and float(r['notional']) else 0.0
  stake_gbp=float(r['notional'])*rate
  econ=economics(gross_pct,stake_gbp=stake_gbp,fixed_cost_gbp=network_floor*rate,proportional_cost_pct=slippage_bps/100.0)
  reality['stake_economics']=econ; reality['measured_roundtrip_network_fee_sol']=network_floor; reality['sol_gbp_rate']=rate; reality['rate_source']=_rate_source
  await record_reality(r['intent_id'],reality,(pnl or {}).get('friction_cost',0.0))
  out.append({'intent_id':r['intent_id'],'entry_price':entry,'mark_price':price,'pnl':pnl,'execution_reality':reality,'sources':sources['source_count']})
  await asyncio.sleep(.15)
 return out

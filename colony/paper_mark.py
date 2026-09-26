"""Mark simulated entries from independent live price providers."""
import asyncio
from colony.sensors import snapshot
from colony.execution_reconcile import pending,reconcile
async def _price(mint):
 s=await snapshot(mint)
 vals=[float(x['price_usd']) for x in s['sources'] if x.get('ok') and x.get('price_usd')]
 return (sum(vals)/len(vals) if vals else None),s
async def mark_pending(run_id='paper-livequote-v1',slippage_bps=100):
 rows=await pending(run_id,200);out=[]
 for r in rows:
  q=r.get('quote') or {}
  if isinstance(q,str):
   import json;q=json.loads(q)
  entry=float(q.get('signal_reference_price') or 0)
  if entry<=0:continue
  price,sources=await _price(r['mint'])
  if not price:continue
  pnl=await reconcile(r['intent_id'],entry,price,slippage_bps,0.0)
  out.append({'intent_id':r['intent_id'],'entry_price':entry,'mark_price':price,'pnl':pnl,'sources':sources['source_count']})
  await asyncio.sleep(.15)
 return out

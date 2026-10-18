"""Bounded best-effort birth-time USD discovery price; never execution proof.
API receive timestamp is not provider tick timestamp. No archival backfilling.
"""
import time,asyncio,math
from collector_dexscreener import fetch as dex_fetch
_WINDOW=[]
_BLOCKED_UNTIL=0.0
_LOCK=asyncio.Lock()
async def capture(mint):
 global _BLOCKED_UNTIL
 async with _LOCK:
  now=time.monotonic()
  _WINDOW[:]=[t for t in _WINDOW if now-t<60]
  if now<_BLOCKED_UNTIL or len(_WINDOW)>=8:return None
  _WINDOW.append(now)
 try:
  prices,error=await asyncio.wait_for(dex_fetch([mint]),timeout=4)
 except Exception:return None
 if error:
  if '429' in error or '403' in error:_BLOCKED_UNTIL=time.monotonic()+900
  return None
 price=prices.get(mint)
 if price is None or not math.isfinite(float(price)) or price<=0:return None
 return {'price_usd':float(price),'price_provider':'dexscreener_at_candidate_birth','price_observed_at':None,'price_received_at_unverified':time.time(),'price_evidence':'discovery_only_no_provider_tick_timestamp'}

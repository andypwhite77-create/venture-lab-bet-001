"""Fresh-only Gecko price acquisition, separate from 120s discovery cache."""
import time
import math
import logging
import marketdata
log=logging.getLogger(__name__)
_BLOCKED_UNTIL=0.0
async def fetch(mints):
 global _BLOCKED_UNTIL
 if time.monotonic()<_BLOCKED_UNTIL:return {},'cooldown'
 found={}
 for start in range(0,len(mints),marketdata.MAX_MULTI):
  batch=mints[start:start+marketdata.MAX_MULTI]
  try:
   payload=await marketdata._get_json(marketdata.GECKO_MULTI_URL.format(addresses=','.join(batch)))
   for item in payload.get('data') or []:
    token=marketdata.normalize_token(item)
    mint=token['mint']
    if mint not in batch:continue
    price=token.get('price_usd')
    if price is not None and math.isfinite(float(price)) and float(price)>0:
     found[mint]=float(price)
  except Exception as exc:
   if '429' in str(exc):_BLOCKED_UNTIL=time.monotonic()+300
   log.warning('fresh Gecko token request failed: %s',type(exc).__name__)
   return found,type(exc).__name__
 return found,None

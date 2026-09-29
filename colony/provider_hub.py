"""Shared provider hub. Jupiter is execution truth; ancillary providers are corroboration only."""
import asyncio,time
from colony.jupiter_quotes import quote,SOL
from colony.sensors import snapshot as corroboration_snapshot
_CACHE={}; LOCKS={}; TTL=20

async def jupiter_entry(mint,lamports,slippage_bps=100):
 key=('jupiter',mint,int(lamports),int(slippage_bps));now=time.monotonic();hit=_CACHE.get(key)
 if hit and now-hit[0]<TTL:return dict(hit[1],cached=True)
 lock=LOCKS.setdefault(key,asyncio.Lock())
 async with lock:
  hit=_CACHE.get(key);now=time.monotonic()
  if hit and now-hit[0]<TTL:return dict(hit[1],cached=True)
  try:
   q=await asyncio.to_thread(quote,SOL,mint,int(lamports),int(slippage_bps));out={'provider':'jupiter','ok':True,'role':'execution_truth','quote':q}
  except Exception as e:out={'provider':'jupiter','ok':False,'role':'execution_truth','error':type(e).__name__}
  _CACHE[key]=(time.monotonic(),out);return out

async def market_snapshot(mint,lamports=None):
 corroboration=await corroboration_snapshot(mint)
 execution=await jupiter_entry(mint,lamports) if lamports else {'provider':'jupiter','ok':None,'role':'execution_truth','reason':'no_size'}
 return {'mint':mint,'execution':execution,'corroboration':corroboration,
  'policy':'Jupiter determines executability; Birdeye/CoinGecko degradation alone never grants or vetoes authority.'}

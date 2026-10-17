"""Read-only Jupiter quote adapter. No transaction building or signing."""
import json,os,time,urllib.parse,urllib.request,urllib.error
KEY=os.getenv('JUPITER_API_KEY','').strip()
BASE='https://api.jup.ag/swap/v1/quote' if KEY else 'https://lite-api.jup.ag/swap/v1/quote'
SOL='So11111111111111111111111111111111111111112'
USDC='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
_CACHE={}
_BACKOFF_UNTIL=0
_LITE_BACKOFF_UNTIL=0
# Per-process safeguards; never substitute stale quotes for a missing observation.
LITE_COOLDOWN_SECONDS=180
class QuoteTransportError(RuntimeError):
 def __init__(self,attempts):
  self.attempts=tuple(attempts)
  super().__init__('jupiter_transport:'+','.join(attempts))
def quote(input_mint,output_mint,amount,slippage_bps=100,timeout=10):
 global _BACKOFF_UNTIL,_LITE_BACKOFF_UNTIL
 ck=(input_mint,output_mint,int(amount),int(slippage_bps)); now=time.time()
 cached=_CACHE.get(ck)
 if cached and now-cached[0] < 2.0:return cached[1]
 q=urllib.parse.urlencode({'inputMint':input_mint,'outputMint':output_mint,'amount':int(amount),'slippageBps':int(slippage_bps)})
 headers=({'x-api-key':KEY} if KEY else {})
 lite='https://lite-api.jup.ag/swap/v1/quote'
 bases=([BASE] if KEY and now>=_BACKOFF_UNTIL else [])
 if now>=_LITE_BACKOFF_UNTIL:bases.append(lite)
 if not KEY and now<_LITE_BACKOFF_UNTIL:raise QuoteTransportError(['lite:cooldown_429'])
 if KEY and not bases:raise QuoteTransportError(['primary:cooldown_429','lite:cooldown_429'])
 data=None;attempts=[];deadline=time.monotonic()+max(0.2,float(timeout))
 for base in bases:
  # A single quote observation has a bounded total network budget, including
  # alternative endpoints. Never wait/retry indefinitely at the due timestamp.
  remaining=deadline-time.monotonic()
  if remaining<=0:break
  req=urllib.request.Request(base+'?'+q,headers=(headers if base==BASE else {}))
  try:
   with urllib.request.urlopen(req,timeout=remaining) as r:data=json.loads(r.read())
   break
  except urllib.error.HTTPError as e:
   is_primary=bool(KEY) and base==BASE
   attempts.append(f'{"primary" if is_primary else "lite"}:http_{e.code}')
   if e.code==429:
    if is_primary:_BACKOFF_UNTIL=time.time()+60
    else:_LITE_BACKOFF_UNTIL=time.time()+LITE_COOLDOWN_SECONDS
   if is_primary and e.code in (429,500,502,503,504):
    continue
   raise QuoteTransportError(attempts) from e
  except (urllib.error.URLError,TimeoutError,ConnectionError) as e:
   attempts.append(f'{"primary" if base==BASE else "lite"}:{type(e).__name__}')
   if base==BASE:continue
   raise QuoteTransportError(attempts) from e
 if data is None:raise QuoteTransportError(attempts or ['quote_deadline_exceeded'])
 result={'input_mint':data['inputMint'],'output_mint':data['outputMint'],'in_amount':data['inAmount'],
  'out_amount':data['outAmount'],'other_amount_threshold':data.get('otherAmountThreshold'),
  'price_impact_pct':float(data.get('priceImpactPct') or 0),'slippage_bps':int(data['slippageBps']),
  'route_labels':[x.get('swapInfo',{}).get('label') for x in data.get('routePlan',[])],
  'context_slot':data.get('contextSlot'),'time_taken':data.get('timeTaken')}
 _CACHE[ck]=(time.time(),result)
 return result

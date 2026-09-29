"""Read-only Jupiter quote adapter. No transaction building or signing."""
import json,os,time,urllib.parse,urllib.request,urllib.error
KEY=os.getenv('JUPITER_API_KEY','').strip()
BASE='https://api.jup.ag/swap/v1/quote' if KEY else 'https://lite-api.jup.ag/swap/v1/quote'
SOL='So11111111111111111111111111111111111111112'
USDC='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
_CACHE={}
_BACKOFF_UNTIL=0
def quote(input_mint,output_mint,amount,slippage_bps=100,timeout=10):
 global _BACKOFF_UNTIL
 ck=(input_mint,output_mint,int(amount),int(slippage_bps)); now=time.time()
 cached=_CACHE.get(ck)
 if cached and now-cached[0] < 2.0:return cached[1]
 q=urllib.parse.urlencode({'inputMint':input_mint,'outputMint':output_mint,'amount':int(amount),'slippageBps':int(slippage_bps)})
 headers=({'x-api-key':KEY} if KEY else {})
 bases=[BASE]
 if KEY and now < _BACKOFF_UNTIL:bases=['https://lite-api.jup.ag/swap/v1/quote']
 elif KEY:bases.append('https://lite-api.jup.ag/swap/v1/quote')
 data=None
 for base in bases:
  req=urllib.request.Request(base+'?'+q,headers=(headers if base==BASE else {}))
  try:
   with urllib.request.urlopen(req,timeout=timeout) as r:data=json.loads(r.read())
   break
  except urllib.error.HTTPError as e:
   if e.code==429 and base==BASE:_BACKOFF_UNTIL=time.time()+60;continue
   raise
 if data is None:raise RuntimeError('jupiter_quote_unavailable')
 result={'input_mint':data['inputMint'],'output_mint':data['outputMint'],'in_amount':data['inAmount'],
  'out_amount':data['outAmount'],'other_amount_threshold':data.get('otherAmountThreshold'),
  'price_impact_pct':float(data.get('priceImpactPct') or 0),'slippage_bps':int(data['slippageBps']),
  'route_labels':[x.get('swapInfo',{}).get('label') for x in data.get('routePlan',[])],
  'context_slot':data.get('contextSlot'),'time_taken':data.get('timeTaken')}
 _CACHE[ck]=(time.time(),result)
 return result

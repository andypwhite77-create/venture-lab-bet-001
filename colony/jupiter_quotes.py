"""Read-only Jupiter quote adapter. No transaction building or signing."""
import json,urllib.parse,urllib.request
BASE='https://lite-api.jup.ag/swap/v1/quote'
SOL='So11111111111111111111111111111111111111112'
USDC='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
def quote(input_mint,output_mint,amount,slippage_bps=100,timeout=10):
 q=urllib.parse.urlencode({'inputMint':input_mint,'outputMint':output_mint,'amount':int(amount),'slippageBps':int(slippage_bps)})
 with urllib.request.urlopen(BASE+'?'+q,timeout=timeout) as r:data=json.loads(r.read())
 return {'input_mint':data['inputMint'],'output_mint':data['outputMint'],'in_amount':data['inAmount'],
  'out_amount':data['outAmount'],'other_amount_threshold':data.get('otherAmountThreshold'),
  'price_impact_pct':float(data.get('priceImpactPct') or 0),'slippage_bps':int(data['slippageBps']),
  'route_labels':[x.get('swapInfo',{}).get('label') for x in data.get('routePlan',[])],
  'context_slot':data.get('contextSlot'),'time_taken':data.get('timeTaken')}

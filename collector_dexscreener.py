"""Independent DexScreener quote fallback; never uses historical price cache."""
import asyncio
import json
import math
import urllib.request
import urllib.error

URL='https://api.dexscreener.com/tokens/v1/solana/'

def _request(mints):
    request=urllib.request.Request(URL+','.join(mints),headers={'Accept':'application/json','User-Agent':'VentureLabResearch/1.0'})
    with urllib.request.urlopen(request,timeout=12) as response:
        return json.load(response)

async def fetch(mints):
    prices={}
    for start in range(0,len(mints),30):
        batch=mints[start:start+30]
        try:
            pairs=await asyncio.to_thread(_request,batch)
            if not isinstance(pairs,list):return prices,'invalid_payload'
            best={}
            for pair in pairs:
                if pair.get('chainId')!='solana':continue
                mint=(pair.get('baseToken') or {}).get('address')
                if mint not in batch:continue
                try:
                    price=float(pair.get('priceUsd'))
                    liquidity=float((pair.get('liquidity') or {}).get('usd') or 0)
                except (TypeError,ValueError,OverflowError):continue
                if not math.isfinite(price) or price<=0 or not math.isfinite(liquidity) or liquidity<=0:continue
                if mint not in best or liquidity>best[mint][0]:best[mint]=(liquidity,price)
            prices.update({mint:price for mint,(_,price) in best.items()})
        except urllib.error.HTTPError as exc:return prices,f'HTTP_{exc.code}'
        except Exception as exc:return prices,type(exc).__name__
    return prices,None

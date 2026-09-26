"""Shared market senses. One fetch per asset; all ants consume the same snapshot."""
import asyncio, json, os, time, urllib.parse, urllib.request, urllib.error

def _get_json(url, headers=None, timeout=10):
    req=urllib.request.Request(url,headers=headers or {})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode())

async def birdeye_price(mint):
    key=os.getenv('BIRDEYE_API_KEY');
    if not key:return {'provider':'birdeye','ok':False,'error':'no_key'}
    url='https://public-api.birdeye.so/defi/price?address='+urllib.parse.quote(mint)
    try:
        x=await asyncio.to_thread(_get_json,url,{'X-API-KEY':key,'x-chain':'solana'})
        d=x.get('data') or {}; return {'provider':'birdeye','ok':bool(x.get('success')),'price_usd':d.get('value'),'raw':d}
    except urllib.error.HTTPError as e:
        body=e.read(300).decode(errors='replace')
        return {'provider':'birdeye','ok':False,'error':f'HTTP_{e.code}','detail':body}
    except Exception as e:return {'provider':'birdeye','ok':False,'error':type(e).__name__}

async def coingecko_price(mint):
    key=os.getenv('COINGECKO_API_KEY');
    if not key:return {'provider':'coingecko','ok':False,'error':'no_key'}
    url='https://api.coingecko.com/api/v3/simple/token_price/solana?contract_addresses='+urllib.parse.quote(mint)+'&vs_currencies=usd'
    try:
        x=await asyncio.to_thread(_get_json,url,{'x-cg-demo-api-key':key})
        d=x.get(mint) or x.get(mint.lower()) or {}; return {'provider':'coingecko','ok':bool(d),'price_usd':d.get('usd'),'raw':d}
    except Exception as e:return {'provider':'coingecko','ok':False,'error':type(e).__name__}

async def snapshot(mint):
    results=await asyncio.gather(birdeye_price(mint),coingecko_price(mint))
    prices=[float(x['price_usd']) for x in results if x.get('ok') and x.get('price_usd')]
    disagreement=None
    if len(prices)>1:
        lo,hi=min(prices),max(prices); disagreement=(hi-lo)/max(lo,1e-18)
    return {'mint':mint,'observed_at':time.time(),'sources':results,'source_count':sum(x.get('ok',False) for x in results),'price_disagreement_ratio':disagreement}

async def main():
    import sys
    print(json.dumps(await snapshot(sys.argv[1]),indent=2))
if __name__=='__main__':asyncio.run(main())

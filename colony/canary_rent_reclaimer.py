"""Conservative Canary token-account rent reclaimer."""
import argparse, asyncio, json, os, urllib.request
from datetime import datetime, timezone
from db import init_db, connection
from colony.canary_controller import rpc_call, wallet_address

SOL='So11111111111111111111111111111111111111112'
USDC='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
TOKEN='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
TOKEN22='TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'
GW='http://127.0.0.1:15888/chains/solana/close-token-account'

async def eligible_mints():
    async with connection() as c:
        rows=await c.fetch("""SELECT mint,max(updated_at) last_closed FROM canary_trade_intents
          WHERE broadcast=true AND status='closed' AND execution->>'mode'='live'
          GROUP BY mint HAVING max(updated_at) < now()-interval '5 minutes'""")
        active=set(await c.fetchval("""SELECT coalesce(array_agg(DISTINCT mint),ARRAY[]::text[])
          FROM canary_trade_intents WHERE status IN
          ('claimed','open','recovery','submitting_entry','submitting_exit','uncertain')"""))
    return {r['mint'] for r in rows if r['mint'] not in active and r['mint'] not in (SOL,USDC)}

def zero_accounts(mints):
    found=[]
    for program in (TOKEN,TOKEN22):
        result=rpc_call('getTokenAccountsByOwner',[wallet_address(),{'programId':program},{'encoding':'jsonParsed','commitment':'finalized'}])
        for item in result.get('value',[]):
            info=item['account']['data']['parsed']['info']; mint=info['mint']
            if mint not in mints or info['tokenAmount']['amount']!='0': continue
            found.append(dict(token_account=item['pubkey'],mint=mint,program=program,lamports=item['account']['lamports']))
    return found

def gateway_close(item,execute=False):
    key=os.environ.get('HUMMINGBOT_GATEWAY_API_KEY','')
    if not key: raise ValueError('gateway_key_missing')
    body=json.dumps(dict(network='mainnet-beta',address=wallet_address(),tokenAccount=item['token_account'],expectedMint=item['mint'],simulateOnly=not execute)).encode()
    req=urllib.request.Request(GW,data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r: return json.load(r)

async def main(execute_one=False):
    await init_db(); mints=await eligible_mints(); accounts=zero_accounts(mints)
    accounts.sort(key=lambda x:x['token_account'])
    if not accounts:
        print(json.dumps({'ok':True,'eligible':0,'message':'no reclaimable Canary token accounts'})); return
    print(json.dumps({'ok':True,'eligible':len(accounts),'reclaimable_sol':sum(x['lamports'] for x in accounts)/1e9}))
    selected=accounts[:1] if execute_one else accounts
    for item in selected:
        try:
            out=await asyncio.to_thread(gateway_close,item,execute_one)
            safe={'account':item['token_account'],'mint':item['mint'],'lamports':item['lamports'],'simulated':out.get('simulated')}
            if execute_one: safe.update(signature=out.get('signature'),fee_sol=out.get('feeSol'))
            print(json.dumps(safe))
        except Exception as e:
            # A live close is never retried here: an HTTP timeout/error can be ambiguous.
            print(json.dumps({'account':item['token_account'],'mint':item['mint'],'ok':False,'error':type(e).__name__,'retry':False}))
            if execute_one: raise

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--execute-one',action='store_true')
    args=p.parse_args(); asyncio.run(main(args.execute_one))

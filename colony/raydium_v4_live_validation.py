"""One-shot verification of published Raydium SOL/USDC V4 pool against read-only vaults.
The observed vault ratio is not an execution price: open orders and unsettled PnL are excluded.
"""
import asyncio,base64,json,os,urllib.request,time
from colony.raydium_v4_pool_verify import verify
from colony.solana_vault_spot import probe_vaults
POOL='58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2'
BASE='So11111111111111111111111111111111111111112'
QUOTE='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
BASE_VAULT='DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz'
QUOTE_VAULT='HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz'
def request_pool(url):
 body=json.dumps({'jsonrpc':'2.0','id':1,'method':'getAccountInfo','params':[POOL,{'encoding':'base64','commitment':'confirmed'}]}).encode()
 with urllib.request.urlopen(urllib.request.Request(url,data=body,headers={'Content-Type':'application/json'}),timeout=8) as r:return json.load(r)
async def run(url=None):
 url=url or os.getenv('SOLANA_SECONDARY_RPC_URL','https://api.mainnet-beta.solana.com')
 fetched=await asyncio.to_thread(request_pool,url)
 if fetched.get('error'):raise RuntimeError('pool RPC failed')
 envelope=fetched['result'];pool=envelope['value']
 if not pool:raise RuntimeError('pool missing')
 match=verify(base64.b64decode(pool['data'][0]),pool['owner'],BASE_VAULT,QUOTE_VAULT,BASE,QUOTE)
 vault=await probe_vaults(BASE_VAULT,QUOTE_VAULT,BASE,QUOTE,url)
 if not vault.get('ok'):raise RuntimeError('vault validation failed')
 return {'pool_address':POOL,'pool_slot':envelope['context']['slot'],'vault_slot':vault['slot'],'verified_pool_fields':match,'reserve_ratio_usdc_per_sol':vault['b_per_a'],'received_at':time.time(),'pool_membership_verified':True,'indicative_only':True,'executable_quote':False,'excluded':'open orders, pending PnL, swap fees, route selection, price impact'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

"""Research-only RPC pool-account probe. No price inference, signing, or orders.
Explicit pool address required; RPC account bytes cannot be treated as a quote.
"""
import asyncio,json,os,time,urllib.request

def _rpc(url,address):
 payload=json.dumps({'jsonrpc':'2.0','id':1,'method':'getAccountInfo','params':[address,{'encoding':'base64','commitment':'confirmed'}]}).encode()
 req=urllib.request.Request(url,data=payload,headers={'Content-Type':'application/json','User-Agent':'VentureLabReadOnlyProbe/1.0'})
 with urllib.request.urlopen(req,timeout=8) as response:return json.load(response)
async def probe(address,url=None):
 if not isinstance(address,str) or not 32<=len(address)<=44 or not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):raise ValueError('invalid Solana address')
 url=url or os.getenv('SOLANA_SECONDARY_RPC_URL','https://api.mainnet-beta.solana.com')
 received=time.time()
 result=await asyncio.to_thread(_rpc,url,address)
 if 'error' in result:return {'ok':False,'error':result['error'],'authority':'research_only'}
 wrapper=result.get('result') or {};account=wrapper.get('value')
 if not account:return {'ok':False,'reason':'account_not_found','slot':(wrapper.get('context') or {}).get('slot'),'authority':'research_only'}
 return {'ok':True,'address':address,'slot':(wrapper.get('context') or {}).get('slot'),'received_at':received,'owner':account.get('owner'),'lamports':account.get('lamports'),'data_encoding':'base64','data_length':len((account.get('data') or [''])[0]),'indicative_price':None,'execution_quote':None,'authority':'research_only_no_prices_or_orders'}
if __name__=='__main__':
 import sys
 print(json.dumps(asyncio.run(probe(sys.argv[1]))))

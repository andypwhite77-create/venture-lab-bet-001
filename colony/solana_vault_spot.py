"""Read-only two-vault AMM reserve evidence. Does NOT assert pool membership or executable prices.
Callers must independently verify both vaults belong to the SAME constant-product pool.
"""
import asyncio,json,math,os,time,urllib.request
from decimal import Decimal
from colony.solana_pool_probe import _rpc as _single_rpc

def validate_vault(v,expected_mint):
 if not isinstance(v,dict) or v.get('owner') not in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA','TokenzQdBNbLqP5VEhdkAS6EPFDTFxQPAkhXyYP9G1g'):
  raise ValueError('account not owned by supported SPL token program')
 parsed=((v.get('data') or {}).get('parsed') or {})
 if parsed.get('type')!='account':raise ValueError('not parsed SPL token account')
 info=parsed.get('info') or {};amount=info.get('tokenAmount') or {}
 if info.get('mint')!=expected_mint:raise ValueError('mint mismatch')
 raw=amount.get('amount');decimals=amount.get('decimals')
 if not isinstance(raw,str) or not raw.isdecimal() or not isinstance(decimals,int) or not 0<=decimals<=18:raise ValueError('invalid token quantity')
 if int(raw)<=0:raise ValueError('empty vault')
 return Decimal(int(raw))/(Decimal(10)**decimals)

def spot(vault_a,vault_b,mint_a,mint_b):
 a=validate_vault(vault_a,mint_a);b=validate_vault(vault_b,mint_b)
 if a<=0 or b<=0:raise ValueError('empty reserves')
 return {'reserve_a':str(a),'reserve_b':str(b),'b_per_a':str(b/a),'authority':'unverified_amm_reserve_ratio_not_execution_quote','fees_included':False,'pool_membership_verified':False}

def _request(url,addresses):
 payload=json.dumps({'jsonrpc':'2.0','id':1,'method':'getMultipleAccounts','params':[addresses,{'encoding':'jsonParsed','commitment':'confirmed'}]}).encode()
 req=urllib.request.Request(url,data=payload,headers={'Content-Type':'application/json','User-Agent':'VentureLabReadOnlyProbe/1.0'})
 with urllib.request.urlopen(req,timeout=8) as response:return json.load(response)
async def probe_vaults(vault_a,vault_b,mint_a,mint_b,url=None):
 for addr in (vault_a,vault_b,mint_a,mint_b):
  if not isinstance(addr,str) or not 32<=len(addr)<=44 or not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in addr):raise ValueError('invalid Solana address')
 url=url or os.getenv('SOLANA_SECONDARY_RPC_URL','https://api.mainnet-beta.solana.com')
 payload=await asyncio.to_thread(_request,url,[vault_a,vault_b])
 if payload.get('error'):return {'ok':False,'rpc_error':payload['error']}
 result=payload.get('result') or {};values=result.get('value') or []
 if len(values)!=2 or not all(values):return {'ok':False,'reason':'vault_unavailable'}
 return {'ok':True,'slot':(result.get('context') or {}).get('slot'),'received_at':time.time(),**spot(values[0],values[1],mint_a,mint_b)}

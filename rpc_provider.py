"""Central Solana RPC provider with Helius budget isolation and optional failover."""
import os, httpx
from budget import assert_budget_available, estimate_credits, record_rpc_usage

HELIUS_KEY=os.getenv('HELIUS_API_KEY','')
HELIUS_URL=f'https://mainnet.helius-rpc.com/?api-key={HELIUS_KEY}' if HELIUS_KEY else ''
SECONDARY_URL=os.getenv('SOLANA_SECONDARY_RPC_URL','').strip()

async def _post(url,method,params):
 payload={'jsonrpc':'2.0','id':1,'method':method,'params':params or []}
 async with httpx.AsyncClient(timeout=25.0) as client:
  r=await client.post(url,json=payload);r.raise_for_status();body=r.json()
 if 'error' in body: raise RuntimeError(str(body['error']))
 return body.get('result')

async def rpc_call(method,params=None,db_ok=True):
 """Prefer Helius while within its explicit budget; fail over without charging Helius usage."""
 errors=[]
 if HELIUS_URL:
  try:
   credits=estimate_credits(method)
   if db_ok: await assert_budget_available(credits)
   result=await _post(HELIUS_URL,method,params)
   if db_ok: await record_rpc_usage(method,credits)
   return result,'helius'
  except Exception as exc: errors.append(f'helius:{exc}')
 if SECONDARY_URL:
  try:return await _post(SECONDARY_URL,method,params),'secondary'
  except Exception as exc: errors.append(f'secondary:{exc}')
 raise RuntimeError('RPC unavailable: '+'; '.join(errors))

def configured(): return {'helius':bool(HELIUS_URL),'secondary':bool(SECONDARY_URL)}

"""Domain-agnostic colony drives with a trading application profile.
Drives shape experiments only; they grant no trading, capital or fission authority.
"""
import asyncio, json, os, time, urllib.request
from db import connection

FISSION_PROFIT_GBP=1_000_000.0
_fx={'rate':None,'at':0.0}


def _sol_gbp_sync():
    now=time.time()
    if _fx['rate'] is not None and now-_fx['at']<900: return _fx['rate']
    try:
        req=urllib.request.Request('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=gbp',headers={'x-cg-demo-api-key':os.getenv('COINGECKO_API_KEY','')})
        with urllib.request.urlopen(req,timeout=4) as r: rate=float(json.load(r)['solana']['gbp'])
        _fx.update(rate=rate,at=now); return rate
    except Exception:
        return _fx['rate']

async def snapshot():
    async with connection() as c:
        net_sol=float(await c.fetchval("SELECT coalesce(sum(net_pnl),0) FROM colony_execution_ledger WHERE run_id='colony-native-v1' AND net_pnl IS NOT NULL") or 0)
    rate=await asyncio.to_thread(_sol_gbp_sync)
    profit_gbp=(net_sol*rate) if rate is not None else None
    progress=(max(0.0,profit_gbp)/FISSION_PROFIT_GBP) if profit_gbp is not None else 0.0
    return {
      'version':'colony-drives-v1','authority':'motivation_only',
      'application_profile':'trading',
      'core_motivation':'acquire sustainable resources; preserve colony; reproduce validated structures; expand useful capacity; fission only from extraordinary surplus',
      'drives':{
        'acquire':{'resource':'realisable net capital after costs','current_net_sol':net_sol,'current_net_gbp':profit_gbp},
        'survive':{'objective':'avoid catastrophic loss and preserve adaptive capacity'},
        'reproduce':{'objective':'convert validated bloodline success into bounded nursery brood'},
        'expand':{'objective':'grow useful non-redundant workers when evidence and resources justify it'},
        'fission':{'visible':True,'spawn_authority':False,'threshold_profit_gbp':FISSION_PROFIT_GBP,
                   'current_profit_gbp':profit_gbp,'progress_fraction':min(1.0,progress),
                   'eligible':bool(profit_gbp is not None and profit_gbp>=FISSION_PROFIT_GBP),
                   'rule':'£1,000,000 cumulative realised profit earns eligibility to propose a daughter colony; spawning still requires explicit human authorization'}
      }}

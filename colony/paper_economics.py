"""Paper/live-canary stake economics.

Keeps strategy quality separate from capital size while modelling whether a signal can
actually survive fixed and proportional execution costs at the intended canary stake.
No live authority lives here.
"""
from __future__ import annotations
import json, os, time, urllib.request

TARGET_STAKE_GBP=float(os.getenv('PAPER_STAKE_GBP','25'))
RATE_TTL_SECONDS=300
_rate={'value':None,'at':0.0,'source':None}

def sol_gbp_rate():
    now=time.time()
    if _rate['value'] is not None and now-_rate['at'] < RATE_TTL_SECONDS:
        return float(_rate['value']), _rate['source']
    try:
        req=urllib.request.Request('https://api.kraken.com/0/public/Ticker?pair=SOLGBP',headers={'User-Agent':'venture-lab-paper/1.0'})
        with urllib.request.urlopen(req,timeout=4) as r:
            body=json.load(r)
        result=body.get('result') or {}
        row=next(iter(result.values()))
        rate=float(row['c'][0])
        if rate <= 0: raise ValueError('bad_rate')
        _rate.update(value=rate,at=now,source='kraken_public')
        return rate,'kraken_public'
    except Exception:
        fallback=float(os.getenv('PAPER_SOL_GBP_FALLBACK','90.36'))
        if _rate['value'] is not None:
            return float(_rate['value']),str(_rate['source'])+'-cached'
        _rate.update(value=fallback,at=now,source='configured_fallback')
        return fallback,'configured_fallback'

def notional_sol(stake_gbp: float=TARGET_STAKE_GBP):
    rate,source=sol_gbp_rate()
    return float(stake_gbp)/rate,rate,source

async def measured_roundtrip_network_fee_sol(conn,hours:int=24):
    """Two transactions using the median fee of recent successful observed Jupiter txs."""
    median=await conn.fetchval("""SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY fee_lamports)
      FROM observed_transactions WHERE success=true AND fee_lamports IS NOT NULL
      AND block_time >= now()-($1 * interval '1 hour')""",int(hours))
    return (2.0*float(median)/1_000_000_000.0) if median is not None else 0.0

def adjusted_return_pct(return_pct:float, stake_gbp:float=TARGET_STAKE_GBP, fixed_cost_gbp:float=0.0):
    """Apply fixed execution cost to a return already net of proportional friction."""
    if float(stake_gbp) <= 0: return float(return_pct)
    return float(return_pct) - (float(fixed_cost_gbp)/float(stake_gbp)*100.0)

def economics(return_pct:float, stake_gbp:float=TARGET_STAKE_GBP, fixed_cost_gbp:float=0.0, proportional_cost_pct:float=0.0):
    stake=float(stake_gbp); gross_pct=float(return_pct); prop_pct=float(proportional_cost_pct)
    gross_gbp=stake*gross_pct/100.0
    variable_cost=stake*prop_pct/100.0
    net_gbp=gross_gbp-variable_cost-float(fixed_cost_gbp)
    net_pct=(net_gbp/stake*100.0) if stake else 0.0
    margin_pct=gross_pct-prop_pct
    break_even=(float(fixed_cost_gbp)/(margin_pct/100.0)) if margin_pct>0 and fixed_cost_gbp>0 else (0.0 if margin_pct>0 else None)
    return {'stake_gbp':stake,'gross_return_pct':gross_pct,'gross_profit_gbp':gross_gbp,
            'fixed_cost_gbp':float(fixed_cost_gbp),'proportional_cost_pct':prop_pct,
            'net_profit_gbp':net_gbp,'net_return_pct':net_pct,'break_even_stake_gbp':break_even}

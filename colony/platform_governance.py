"""Swarm economics, provider resilience and deterministic graduation telemetry.
Observational/governance only: never buys services, signs transactions or raises live authority.
"""
import json, os
from db import connection

MONTHLY_VPS_GBP=float(os.getenv('SWARM_VPS_MONTHLY_GBP','0'))
MONTHLY_DATA_GBP=float(os.getenv('SWARM_DATA_MONTHLY_GBP','0'))
MONTHLY_AI_GBP=float(os.getenv('SWARM_AI_MONTHLY_GBP','0'))
MONTHLY_OTHER_GBP=float(os.getenv('SWARM_OTHER_MONTHLY_GBP','0'))

async def ensure_schema(c):
    await c.execute('''CREATE TABLE IF NOT EXISTS swarm_cost_ledger(
      id BIGSERIAL PRIMARY KEY, observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      category TEXT NOT NULL, provider TEXT, amount_gbp DOUBLE PRECISION NOT NULL,
      note TEXT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb)''')
    await c.execute('''CREATE TABLE IF NOT EXISTS colony_graduation_state(
      family TEXT PRIMARY KEY, stage TEXT NOT NULL DEFAULT 'historical',
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
      live_authority BOOLEAN NOT NULL DEFAULT false)''')

async def provider_snapshot(c):
    rows=await c.fetch('''SELECT provider,count(*) n,count(*) FILTER(WHERE ok) ok_n,
      max(observed_at) last_seen,max(observed_at) FILTER(WHERE ok) last_ok,
      (array_agg(error ORDER BY observed_at DESC))[1] last_error
      FROM colony_provider_health WHERE observed_at>now()-interval '24 hours' GROUP BY provider''')
    out=[]
    for r in rows:
        d=dict(r); d['success_pct']=100*int(r['ok_n'])/max(1,int(r['n']))
        d['state']='healthy' if d['success_pct']>=90 else ('degraded' if d['success_pct']>=50 else 'failing')
        out.append(d)
    return out
async def economics_snapshot(c, sol_gbp=None):
    month=await c.fetchrow('''SELECT coalesce(sum(amount_gbp),0) actual_costs,
      coalesce(sum(amount_gbp) FILTER(WHERE category='data'),0) data_costs,
      coalesce(sum(amount_gbp) FILTER(WHERE category='ai'),0) ai_costs
      FROM swarm_cost_ledger WHERE observed_at>=date_trunc('month',now())''')
    pnl=await c.fetchval("SELECT coalesce(sum(net_pnl),0) FROM colony_execution_ledger WHERE net_pnl IS NOT NULL AND created_at>=date_trunc('month',now())")
    budgeted=MONTHLY_VPS_GBP+MONTHLY_DATA_GBP+MONTHLY_AI_GBP+MONTHLY_OTHER_GBP
    research_gbp=float(pnl or 0)*(float(sol_gbp) if sol_gbp else 0.0)
    costs=max(float(month['actual_costs'] or 0),budgeted)
    return {'research_net_gbp':research_gbp,'actual_costs_gbp':float(month['actual_costs'] or 0),
      'budgeted_monthly_cost_gbp':budgeted,'free_cash_flow_gbp':research_gbp-costs,
      'self_funding':bool(costs>0 and research_gbp>=costs),'basis':'research ledger; no live revenue claimed',
      'configured':{'vps':MONTHLY_VPS_GBP,'data':MONTHLY_DATA_GBP,'ai':MONTHLY_AI_GBP,'other':MONTHLY_OTHER_GBP}}

async def graduation_snapshot(c):
    families=('reversal','momentum','order_flow','wallet_convergence'); out=[]
    for fam in families:
        prod=await c.fetchval("SELECT count(*) FROM colony_genomes WHERE family=$1 AND status='production'",fam)
        hist=await c.fetchrow("SELECT tested_genomes,jsonb_array_length(finalists) finalists,created_at FROM historical_nursery_runs WHERE family=$1 ORDER BY created_at DESC LIMIT 1",fam)
        state=await c.fetchrow("SELECT stage,live_authority,evidence,updated_at FROM colony_graduation_state WHERE family=$1",fam)
        stage=(state['stage'] if state else ('prospective' if prod else 'historical'))
        out.append({'family':fam,'stage':stage,'production_elites':int(prod or 0),'live_authority':bool(state['live_authority']) if state else False,
          'historical_tested':int(hist['tested_genomes']) if hist else 0,'historical_finalists':int(hist['finalists']) if hist else 0,
          'rule':'historical -> prospective -> live_canary -> earned_capital; authority never inferred from P&L'})
    return out

async def snapshot(sol_gbp=None):
    async with connection() as c:
        await ensure_schema(c)
        return {'providers':await provider_snapshot(c),'economics':await economics_snapshot(c,sol_gbp),'graduation':await graduation_snapshot(c)}

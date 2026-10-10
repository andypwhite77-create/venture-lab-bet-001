"""Swarm Queen's scheduled evidence-to-proposal scout.

The hostile-market metaphor motivates rigorous research, not manipulation.
Every generated proposal is advisory, non-executable and human-reviewed.
"""
import asyncio,json
from db import init_db,connection
from colony.queen_opportunity_queue import ensure_schema,submit

async def scout():
 await init_db()
 async with connection() as c:
  await ensure_schema(c)
  await c.execute("""CREATE TABLE IF NOT EXISTS queen_proposal_scout_runs(
    scout_day DATE PRIMARY KEY,ran_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    proposals INTEGER NOT NULL DEFAULT 0,diagnostics JSONB NOT NULL DEFAULT '{}')""")
  inserted=await c.fetchval("""INSERT INTO queen_proposal_scout_runs(scout_day)
    VALUES((now() AT TIME ZONE 'Europe/London')::date)
    ON CONFLICT DO NOTHING RETURNING scout_day""")
  if not inserted:return {'status':'already_scanned_today'}
  metrics=await c.fetchrow("""SELECT count(*)::int total,
    count(*) FILTER(WHERE status='rejected' AND reason IN ('gateway_no_route_found','quote_price_impact'))::int blocked,
    count(*) FILTER(WHERE status='closed' AND broadcast)::int closed
    FROM canary_trade_intents WHERE created_at>=now()-interval '10 days'""")
  risks=await c.fetchrow("""SELECT count(*)::int failures,
    count(*) FILTER(WHERE observation_kind='trending_unavailable')::int missing
    FROM colony_market_ingress WHERE observed_at>=now()-interval '48 hours'""")
  metric=dict(metrics);feeds=dict(risks);count=0
  # Queue evidence, not imaginary profit forecasts. No direct side effects.
  if metric['blocked']>=2:
   exists=await c.fetchval("""SELECT 1 FROM queen_opportunity_proposals
    WHERE submitted_by='swarm_queen_scout' AND kind='market_dislocation'
      AND created_at>=now()-interval '7 days' LIMIT 1""")
   if not exists:
    await submit(c,'market_dislocation','Hostile-market execution-route reconnaissance',
      'Investigate why apparently attractive microcap signals cannot be entered or exited reliably. Compare pre-entry round-trip quotes and liquidity before proposing any trade-filter change.',
      'swarm_queen_scout',
      {'10_day_signal_counts':metric,'source':'canary_trade_intents','measurement':'actual intent status; not a return forecast'},
      ['Quote availability may change between checks','Liquidity can evaporate during exit','Rejecting unroutable orders may also remove winners'],
      {'scope':'shadow quote feasibility study; no trade cap changes'},'Market engagement: detect traps before advancing.')
    count+=1
  if feeds['missing']>=1:
   exists=await c.fetchval("""SELECT 1 FROM queen_opportunity_proposals
    WHERE submitted_by='swarm_queen_scout' AND kind='research_infrastructure'
      AND created_at>=now()-interval '7 days' LIMIT 1""")
   if not exists:
    await submit(c,'research_infrastructure','Reinforce market sensor coverage against 429 failures',
      'Assess read-only alternative data providers, cache strategy and request budgets to reduce blind spots from rate-limited feeds.',
      'swarm_queen_scout',{'48_hour_ingress_counts':feeds,'source':'colony_market_ingress'},
      ['Additional data cost may exceed benefit','Alternative vendors can have similar outages'],
      {'scope':'research only; no new vendor subscription'},'Sensor resilience rather than unverified promises.')
    count+=1
  await c.execute("UPDATE queen_proposal_scout_runs SET proposals=$2,diagnostics=$3::jsonb WHERE scout_day=$1",
    inserted,count,json.dumps({'canary':metric,'feeds':feeds}))
  return {'status':'scanned','created':count,'metrics':metric,'feeds':feeds}
if __name__=='__main__':print(json.dumps(asyncio.run(scout()),default=str))

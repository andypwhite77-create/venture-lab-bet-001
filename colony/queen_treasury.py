"""Queen economic treasury: conservative evidence and resource accounting, advisory only."""
import asyncio,json,os
from db import init_db,connection
SCHEMA='''CREATE TABLE IF NOT EXISTS queen_treasury_costs(id bigserial PRIMARY KEY,queen text NOT NULL,cost_usd numeric NOT NULL CHECK(cost_usd>=0),cost_type text NOT NULL,source text NOT NULL,incurred_at timestamptz NOT NULL DEFAULT now()); CREATE TABLE IF NOT EXISTS queen_treasury_reviews(id bigserial PRIMARY KEY,reviewed_at timestamptz NOT NULL DEFAULT now(),report jsonb NOT NULL);'''
def evaluate(eth_rows,sol_rows,cost_rows):
 costs={}
 for r in cost_rows:costs[r['queen']]=costs.get(r['queen'],0)+float(r['cost_usd'])
 eth_pnl=sum(float(r['net_pnl_usd']) for r in eth_rows if r['status']=='closed' and r['net_pnl_usd'] is not None)
 eth_closed=sum(r['status']=='closed' and r['net_pnl_usd'] is not None for r in eth_rows)
 eth_open=sum(r['status']=='open' for r in eth_rows)
 sol_pnl=sum(float(r['attributed_net_sol']) for r in sol_rows)
 return {'eth':{'aggregate_independent_genome_paper_marks_usd':round(eth_pnl,6),'paper_closed_trades':eth_closed,'open_paper_positions':eth_open,'logged_resource_cost_usd':round(costs.get('eth',0),4),'hypothetical_marks_less_logged_cost_usd':round(eth_pnl-costs.get('eth',0),4),'capital_reserved_usd':25*eth_open,'evidence':'ohlc_paper_not_executable'},'solana':{'executor_recorded_attributed_pnl_sol':round(sol_pnl,10),'logged_resource_cost_usd':round(costs.get('solana',0),4),'evidence':'not_independently_chain_reconciled'},'swarm':{'logged_resource_cost_usd':round(costs.get('swarm',0),4)},'cost_coverage':'Incomplete until VPS/API/inference metering is ingested. Zero logged cost does not mean free.','decision':'No upgrades or retirement from unverified profitability; research prioritisation only.','authority':'read_only_no_live_capital'}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  eth=await c.fetch('SELECT status,net_pnl_usd FROM eth_evolution_paper')
  sol=await c.fetch('SELECT attributed_net_sol FROM ant_wallet_attribution')
  costs=await c.fetch('SELECT queen,cost_usd FROM queen_treasury_costs')
  report=evaluate(eth,sol,costs)
  await c.execute('INSERT INTO queen_treasury_reviews(report) VALUES($1::jsonb)',json.dumps(report))
 return report
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

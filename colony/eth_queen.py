"""Isolated ETH paper-only queen. No keys, transactions, or leverage.
5-minute closed Kraken ETH/USD candles; one-bar prospective paper decisions.
"""
import asyncio,json,logging,time
from datetime import datetime,timezone
import httpx
from colony.eth_opportunity_scout import observe as scout_opportunities
from db import init_db,connection
from colony.eth_evolution import seeds,signal_genome,child_of
log=logging.getLogger(__name__)
URL='https://api.kraken.com/0/public/OHLC?pair=ETHUSD&interval=5'
SCHEMA='''CREATE TABLE IF NOT EXISTS eth_queen_paper(
 candle_time bigint NOT NULL,strategy text NOT NULL,entry_usd double precision NOT NULL,
 exit_usd double precision,net_pnl_usd double precision,status text NOT NULL,
 observed_at timestamptz NOT NULL DEFAULT now(),closed_at timestamptz,
 PRIMARY KEY(candle_time,strategy));'''
EVOLUTION_SCHEMA='''CREATE TABLE IF NOT EXISTS eth_evolution_genomes(id text PRIMARY KEY,direction text NOT NULL,lookback int NOT NULL,threshold double precision NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),parent_id text,status text NOT NULL DEFAULT 'research'); CREATE TABLE IF NOT EXISTS eth_evolution_paper(candle_time bigint NOT NULL,genome_id text NOT NULL,entry_usd double precision NOT NULL,exit_usd double precision,net_pnl_usd double precision,status text NOT NULL DEFAULT 'open',PRIMARY KEY(candle_time,genome_id));'''
STRATEGIES=('momentum','reversal')
START_USD=125.0
STAKE_USD=25.0
ROUND_TRIP_COST_PCT=0.4

def signal(name,closed):
 if len(closed)<4:return False
 last=float(closed[-1][4]);prior=float(closed[-2][4]);older=float(closed[-3][4]);
 if min(last,prior,older)<=0:return False
 return (last>prior>older) if name=='momentum' else (last<prior<older)

def net_pnl(entry,exit,stake=STAKE_USD):
 return stake*((float(exit)/float(entry)-1)-ROUND_TRIP_COST_PCT/100)

async def cycle():
 async with httpx.AsyncClient(timeout=15) as client:
  response=await client.get(URL);response.raise_for_status();data=response.json()
 if data.get('error'):raise ValueError('kraken_provider_error')
 pairs=data.get('result') or {};key=next(k for k in pairs if k!='last')
 candles=sorted(pairs[key],key=lambda x:int(x[0]))
 # Kraken's final OHLC row is still forming. Only use fully closed candles.
 closed=[c for c in candles[:-1] if float(c[4])>0]
 if len(closed)<4:raise ValueError('insufficient_closed_ohlc')
 async with connection() as c:
  await c.execute(SCHEMA)
  await c.execute(EVOLUTION_SCHEMA)
  scouting=await scout_opportunities(c,closed)
  for gid,direction,lookback,threshold in seeds():
   await c.execute('INSERT INTO eth_evolution_genomes(id,direction,lookback,threshold) VALUES($1,$2,$3,$4) ON CONFLICT DO NOTHING',gid,direction,lookback,threshold)
  await c.execute('''UPDATE eth_evolution_paper SET exit_usd=$1,net_pnl_usd=25*(($1/entry_usd-1)-0.004),status='closed' WHERE status='open' AND candle_time<$2''',float(closed[-1][4]),int(closed[-1][0]))
  genomes=await c.fetch('SELECT id,direction,lookback,threshold FROM eth_evolution_genomes WHERE status=$1 ORDER BY created_at LIMIT 20','research')
  for g in genomes:
   n,pnl=await c.fetchrow('SELECT count(*) n,coalesce(sum(net_pnl_usd),0) pnl FROM eth_evolution_paper WHERE genome_id=$1 AND status=$2',g['id'],'closed')
   active=await c.fetchval('SELECT count(*) FROM eth_evolution_paper WHERE genome_id=$1 AND status=$2',g['id'],'open')
   if n>=25 and pnl<=0:
    await c.execute('UPDATE eth_evolution_genomes SET status=$2 WHERE id=$1',g['id'],'research_retired')
    continue
   if n>=25 and pnl>0:
    child=child_of((g['id'],g['direction'],g['lookback'],g['threshold']),int(n))
    await c.execute('INSERT INTO eth_evolution_genomes(id,direction,lookback,threshold,parent_id) VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING',*child,g['id'])
   if 125+float(pnl)-25*active>=25 and signal_genome(g['direction'],g['lookback'],g['threshold'],closed):
    await c.execute('INSERT INTO eth_evolution_paper(candle_time,genome_id,entry_usd) VALUES($1,$2,$3) ON CONFLICT DO NOTHING',int(closed[-1][0]),g['id'],float(closed[-1][4]))
  await c.execute('''UPDATE eth_queen_paper SET exit_usd=$1,net_pnl_usd=25*(($1/entry_usd-1)-0.004),status='closed',closed_at=now()
    WHERE status='open' AND candle_time<$2''',float(closed[-1][4]),int(closed[-1][0]))
  latest=await c.fetch('''SELECT strategy,count(*) n,coalesce(sum(net_pnl_usd),0) pnl FROM eth_queen_paper WHERE status='closed' GROUP BY strategy''')
  stats={r['strategy']:(r['n'],float(r['pnl'])) for r in latest}
  # Selection never looks at unreleased/future price data.
  preferred=max(STRATEGIES,key=lambda name:(stats.get(name,(0,0))[1] if stats.get(name,(0,0))[0]>=10 else -999))
  if all(stats.get(n,(0,0))[0]<10 for n in STRATEGIES):preferred='momentum'
  for name in STRATEGIES:
   n,pnl=stats.get(name,(0,0))
   open_n=await c.fetchval("SELECT count(*) FROM eth_queen_paper WHERE strategy=$1 AND status='open'",name)
   # Research each arm to ten completed observations, then fund only the
   # stronger positive arm; negative strategies abstain. Never reset history.
   allocated=(n<10 or (name==preferred and pnl>0))
   cash=max(0,START_USD+pnl-STAKE_USD*open_n)
   if allocated and cash>=STAKE_USD and signal(name,closed):
    await c.execute('''INSERT INTO eth_queen_paper(candle_time,strategy,entry_usd,status) VALUES($1,$2,$3,'open') ON CONFLICT DO NOTHING''',int(closed[-1][0]),name,float(closed[-1][4]))
  open_count=await c.fetchval("SELECT count(*) FROM eth_queen_paper WHERE status='open'")
 return {'source':'Kraken closed ETH/USD 5m OHLC','strategy_preference':preferred,'research_pnl':stats,'open_paper_positions':open_count,'authority':'paper_only_no_wallet_no_signer','cost_pct':ROUND_TRIP_COST_PCT,'swing_scout':scouting}

async def main():
 logging.basicConfig(level=logging.INFO)
 await init_db()
 while True:
  try:log.info('eth_queen %s',json.dumps(await cycle()))
  except Exception:log.exception('eth_queen_cycle_failure')
  await asyncio.sleep(60)
if __name__=='__main__':asyncio.run(main())

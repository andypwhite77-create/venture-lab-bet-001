"""Paper-only ETH/SOL research colonies on Kraken public OHLC.

No exchange credentials, wallets or order placement. Uses last CLOSED candle;
an earlier paper position closes against a later observed candle, never its
entry candle. Marks are indicative, not executable orderbook fills.
"""
import asyncio,json,time,datetime,httpx
from db import init_db,connection
from colony.market_ingress import seed_mesh
from colony.queen_opportunity_queue import ensure_schema as ensure_proposals,submit as submit_proposal
BASE='https://api.kraken.com/0/public/OHLC'
PAIRS={'ethereum_scout':'ETHUSD','solana_major_scout':'SOLUSD'}
COST_BPS=30 # Explicit illustrative round-trip friction, not measured execution.
SCHEMA="""CREATE TABLE IF NOT EXISTS colony_paper_observations(
 id BIGSERIAL PRIMARY KEY,colony_id TEXT NOT NULL,pair TEXT NOT NULL,
 candle_ts BIGINT NOT NULL,open_price DOUBLE PRECISION,high_price DOUBLE PRECISION,
 low_price DOUBLE PRECISION,close_price DOUBLE PRECISION NOT NULL,
 volume DOUBLE PRECISION,observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(colony_id,candle_ts));
CREATE TABLE IF NOT EXISTS colony_paper_positions(
 id BIGSERIAL PRIMARY KEY,colony_id TEXT NOT NULL,strategy TEXT NOT NULL,
 entry_ts BIGINT NOT NULL,entry_price DOUBLE PRECISION NOT NULL,
 exit_ts BIGINT,exit_price DOUBLE PRECISION,net_return_pct DOUBLE PRECISION,
 status TEXT NOT NULL DEFAULT 'open',created_at TIMESTAMPTZ DEFAULT now(),
 UNIQUE(colony_id,strategy,entry_ts));
CREATE TABLE IF NOT EXISTS colony_paper_runs(
 id BIGSERIAL PRIMARY KEY,run_at TIMESTAMPTZ DEFAULT now(),report JSONB NOT NULL);
"""
def closed_candles(raw,pair):
 if raw.get('error'):raise ValueError('provider_error')
 data=raw['result'];key=next(x for x in data if x!='last')
 # Kraken includes a current uncommitted bar; exclude unconditionally.
 rows=data[key][:-1]
 return [{'ts':int(r[0]),'open':float(r[1]),'high':float(r[2]),'low':float(r[3]),
   'close':float(r[4]),'volume':float(r[6])} for r in rows]
def momentum_signal(closes):
 if len(closes)<25:return False
 short=sum(closes[-5:])/5;long=sum(closes[-24:])/24
 return short>long*1.003
async def run():
 await init_db();await seed_mesh()
 outputs=[]
 async with httpx.AsyncClient(timeout=18) as h:
  for colony,pair in PAIRS.items():
   try:
    r=await h.get(BASE,params={'pair':pair,'interval':60});r.raise_for_status()
    candles=closed_candles(r.json(),pair)
    if len(candles)<26:raise ValueError('insufficient_closed_bars')
    last=candles[-1];signal=momentum_signal([x['close'] for x in candles])
    async with connection() as c:
     await c.execute(SCHEMA)
     await c.execute("""INSERT INTO colony_mesh_registry(colony_id,ecosystem,stage)
       VALUES($1,$2,'paper_research') ON CONFLICT(colony_id)
       DO UPDATE SET stage='paper_research' WHERE colony_mesh_registry.stage='research_proposed'""",
       colony,'ethereum' if colony=='ethereum_scout' else 'solana')
     # Unique candle timestamp makes this rerun-safe.
     for x in candles[-30:]:
      await c.execute("""INSERT INTO colony_paper_observations
       (colony_id,pair,candle_ts,open_price,high_price,low_price,close_price,volume)
       VALUES($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT DO NOTHING""",
       colony,pair,x['ts'],x['open'],x['high'],x['low'],x['close'],x['volume'])
     # An open position only closes when a newer fully closed hourly bar exists.
     old=await c.fetchrow("""SELECT id,entry_ts,entry_price FROM colony_paper_positions
       WHERE colony_id=$1 AND status='open' ORDER BY id LIMIT 1""",colony)
     if old and last['ts']>old['entry_ts']:
      pct=(last['close']/old['entry_price']-1)*100-COST_BPS/100
      await c.execute("""UPDATE colony_paper_positions SET status='closed',exit_ts=$2,
       exit_price=$3,net_return_pct=$4 WHERE id=$1 AND status='open'""",
       old['id'],last['ts'],last['close'],pct)
     if signal and not await c.fetchval("""SELECT 1 FROM colony_paper_positions
       WHERE colony_id=$1 AND status='open'""",colony):
      await c.execute("""INSERT INTO colony_paper_positions
       (colony_id,strategy,entry_ts,entry_price) VALUES($1,'ma5_vs_ma24',$2,$3)
       ON CONFLICT DO NOTHING""",colony,last['ts'],last['close'])
     stats=await c.fetchrow("""SELECT count(*) FILTER(WHERE status='closed')::int trades,
       avg(net_return_pct) FILTER(WHERE status='closed') avg_net_pct,
       min(net_return_pct) FILTER(WHERE status='closed') worst_pct
       FROM colony_paper_positions WHERE colony_id=$1""",colony)
    outputs.append({'colony':colony,'pair':pair,'last_closed_ts':last['ts'],
      'price_usd':last['close'],'signal':signal,'stats':dict(stats),'status':'paper_only'})
   except Exception as e:
    outputs.append({'colony':colony,'pair':pair,'status':'data_unavailable','error':type(e).__name__})
 async with connection() as c:
  await c.execute(SCHEMA)
  await c.execute('INSERT INTO colony_paper_runs(report) VALUES($1::jsonb)',json.dumps(outputs,default=str))
  # Economic selection remains locked until both independent paper populations
  # have at least 30 measured exits. A proposal never initiates a conversion.
  viable=[o for o in outputs if o.get('status')=='paper_only' and o['stats']['trades']>=30]
  if len(viable)==len(PAIRS):
   best,worst=sorted(viable,key=lambda o:float(o['stats']['avg_net_pct'] or -999),reverse=True)
   advantage=float(best['stats']['avg_net_pct'])-float(worst['stats']['avg_net_pct'])
   if advantage>=1 and float(best['stats']['avg_net_pct'])>0:
    await ensure_proposals(c)
    duplicate=await c.fetchval("SELECT 1 FROM queen_opportunity_proposals WHERE submitted_by='paper_colony_allocator' AND created_at>=now()-interval '14 days' LIMIT 1")
    if not duplicate:
     await submit_proposal(c,'colony_expansion','Examine capital migration toward '+best['pair'],
       'Paper research suggests '+best['pair']+' may offer stronger opportunities than '+worst['pair']+'. Request an independent forward execution and concentration analysis before considering reallocation.',
       'paper_colony_allocator',{'source':'colony_paper_positions','colonies':viable,'mean_pct_gap':advantage,'status':'indicative_not_executable'},
       ['Hourly close marks do not guarantee actual fills','Strategy evidence may not transfer to live size','Allocation changes increase concentration and timing risk'],
       {'scope':'comparison study only; no conversion or bankroll increase'},'Independent challenge needed; paper advantage does not establish expected returns.')
 return outputs
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str))

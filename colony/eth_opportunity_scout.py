"""Prospective ETH price-swing hypotheses; paper-only, never predicts certainty."""
import json
SCHEMA='''CREATE TABLE IF NOT EXISTS eth_opportunity_hypotheses(
 candle_time bigint NOT NULL, hypothesis text NOT NULL, entry_usd double precision NOT NULL,
 target_pct double precision NOT NULL, stop_pct double precision NOT NULL,
 horizon_candles int NOT NULL, observation_count int NOT NULL DEFAULT 0,
 status text NOT NULL DEFAULT 'watching', outcome_pct double precision,
 observed_at timestamptz NOT NULL DEFAULT now(), resolved_at timestamptz,
 PRIMARY KEY(candle_time,hypothesis,target_pct));'''
TARGETS=(0.02,0.03)
HORIZON=12

def hypotheses(closed):
 if len(closed)<13:return []
 p=[float(x[4]) for x in closed[-13:]]
 if min(p)<=0:return []
 change3=p[-1]/p[-4]-1
 change12=p[-1]/p[0]-1
 # Only known information from fully closed candles; no future labels.
 result=[]
 if change3>0.004 and change12>0.006:result.append('continuation')
 if change3 < -0.006 and p[-1]>p[-2]:result.append('bounce')
 return result

async def observe(conn,closed):
 await conn.execute(SCHEMA)
 latest=int(closed[-1][0]);price=float(closed[-1][4])
 pending=await conn.fetch("SELECT candle_time,hypothesis,target_pct,stop_pct,horizon_candles FROM eth_opportunity_hypotheses WHERE status='watching'")
 by_time={int(c[0]):i for i,c in enumerate(closed)}
 for row in pending:
  idx=by_time.get(row['candle_time'])
  if idx is None:continue # missing historical candles: cannot score fairly
  forward=closed[idx+1:]
  if not forward:continue
  entry=await conn.fetchval('SELECT entry_usd FROM eth_opportunity_hypotheses WHERE candle_time=$1 AND hypothesis=$2 AND target_pct=$3',row['candle_time'],row['hypothesis'],row['target_pct'])
  status=None;outcome=None
  for candle in forward[:row['horizon_candles']]:
   high=float(candle[2]);low=float(candle[3]);target=entry*(1+row['target_pct']);stop=entry*(1-row['stop_pct'])
   if low<=stop and high>=target:status='ambiguous_intrabar';break
   if low<=stop:status='stop_first';outcome=-row['stop_pct'];break
   if high>=target:status='target_first';outcome=row['target_pct'];break
  if not status and len(forward)>=row['horizon_candles']:
   status='timeout';outcome=float(forward[row['horizon_candles']-1][4])/entry-1
  if status:
   await conn.execute('''UPDATE eth_opportunity_hypotheses SET status=$4,outcome_pct=$5,resolved_at=now(),observation_count=$6 WHERE candle_time=$1 AND hypothesis=$2 AND target_pct=$3''',row['candle_time'],row['hypothesis'],row['target_pct'],status,outcome,len(forward[:row['horizon_candles']]))
 for name in hypotheses(closed):
  for target in TARGETS:
   await conn.execute('''INSERT INTO eth_opportunity_hypotheses(candle_time,hypothesis,entry_usd,target_pct,stop_pct,horizon_candles) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING''',latest,name,price,target,0.01,HORIZON)
 summary=await conn.fetch('''SELECT hypothesis,target_pct,count(*) FILTER(WHERE status IN ('target_first','stop_first','timeout')) completed,count(*) FILTER(WHERE status='target_first') wins FROM eth_opportunity_hypotheses GROUP BY hypothesis,target_pct ORDER BY hypothesis,target_pct''')
 return {'opportunities':[dict(r) for r in summary],'basis':'forward-only OHLC hypotheses; ambiguous same-bar hits excluded; not executable evidence','authority':'paper_research'}

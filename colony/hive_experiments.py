"""Evidence-backed failure research experiments, not self-authorizing strategies.
Records a benchmark, a falsifiable prediction and subsequent measurement status.
"""
import asyncio,json
from db import init_db,connection
SCHEMA="""CREATE TABLE IF NOT EXISTS hive_experiments(
 id BIGSERIAL PRIMARY KEY,created_at TIMESTAMPTZ DEFAULT now(),
 colony TEXT NOT NULL,kind TEXT NOT NULL,hypothesis TEXT NOT NULL,
 prediction TEXT NOT NULL,metric TEXT NOT NULL,baseline JSONB NOT NULL,
 minimum_forward_trades INTEGER NOT NULL DEFAULT 30,
 status TEXT NOT NULL DEFAULT 'awaiting_prospective_test',
 outcome JSONB NOT NULL DEFAULT '{}'::jsonb,
 UNIQUE(colony,kind,metric,baseline));
CREATE TABLE IF NOT EXISTS hive_experiment_reviews(
 id BIGSERIAL PRIMARY KEY,experiment_id BIGINT REFERENCES hive_experiments(id),
 reviewed_at TIMESTAMPTZ DEFAULT now(),assessment TEXT NOT NULL,
 evidence JSONB NOT NULL DEFAULT '{}'::jsonb);"""
def diagnosis(trades,wins,net,worst):
 if trades<10:return None
 if net>=0:return None
 return {'colony':'solana_research','kind':'live_loss_asymmetry',
 'hypothesis':'Trade winners fail to offset real losses after network fees; challenge entry, exit and liquidity assumptions.',
 'prediction':'Prospective challengers must produce positive realised net returns on an independent later sample, with lower loss concentration than this baseline.',
 'metric':'realized_net_sol_per_trade_after_network_fees',
 'baseline':{'trades':trades,'wins':wins,'net_sol':net,'worst_sol':worst,'source':'closed_broadcast_canary','includes_rent':False},
 'minimum_forward_trades':30}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  r=await c.fetchrow("""SELECT count(*)::int trades,
   count(*) FILTER(WHERE (execution->>'realized_market_pnl_after_network_fees_sol')::numeric>0)::int wins,
   coalesce(sum((execution->>'realized_market_pnl_after_network_fees_sol')::numeric),0)::float8 net,
   coalesce(min((execution->>'realized_market_pnl_after_network_fees_sol')::numeric),0)::float8 worst
   FROM canary_trade_intents WHERE status='closed' AND broadcast
   AND execution ? 'realized_market_pnl_after_network_fees_sol'
   AND created_at>=now()-interval '7 days'""")
  x=diagnosis(int(r['trades']),int(r['wins']),float(r['net']),float(r['worst']))
  if not x:return {'status':'no_negative_experiment_trigger','sample':dict(r)}
  # Frozen benchmark; a new daily diagnostic may create a separate baseline.
  ident=await c.fetchval("""INSERT INTO hive_experiments
   (colony,kind,hypothesis,prediction,metric,baseline,minimum_forward_trades)
   VALUES($1,$2,$3,$4,$5,$6::jsonb,$7) ON CONFLICT DO NOTHING RETURNING id""",
   x['colony'],x['kind'],x['hypothesis'],x['prediction'],x['metric'],
   json.dumps(x['baseline']),x['minimum_forward_trades'])
  return {'status':'created' if ident else 'existing_baseline','id':ident,'experiment':x}
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str))

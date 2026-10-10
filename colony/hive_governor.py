"""Independent loss governor; disarms *new entries* only, never signs exits.
Use explicit, immutable absolute loss limits. Only a human may re-arm.
"""
import asyncio,json,os
from db import init_db,connection

LIMIT_SOL=float(os.getenv('HIVE_MAX_7D_LOSS_SOL','0.01'))
MIN_TRADES=int(os.getenv('HIVE_MIN_TRADES_FOR_LOSS_STOP','10'))
SCHEMA="""CREATE TABLE IF NOT EXISTS hive_governor_audit(
 id BIGSERIAL PRIMARY KEY,checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 seven_day_net_sol DOUBLE PRECISION NOT NULL,trade_count INTEGER NOT NULL,
 decision TEXT NOT NULL,details JSONB NOT NULL DEFAULT '{}');"""

def verdict(trades,net_sol):
 if trades>=MIN_TRADES and net_sol<=-LIMIT_SOL:return 'disarm_loss_limit'
 return 'observe'

async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  row=await c.fetchrow("""SELECT count(*)::int trades,
   coalesce(sum((execution->>'realized_market_pnl_after_network_fees_sol')::numeric),0)::float8 net_sol
   FROM canary_trade_intents WHERE broadcast AND status='closed'
   AND execution ? 'realized_market_pnl_after_network_fees_sol'
   AND created_at>=now()-interval '7 days'""")
  n=int(row['trades']);net=float(row['net_sol'])
  decision=verdict(n,net)
  detail={'threshold_sol':LIMIT_SOL,'min_trades':MIN_TRADES,'excludes_rent':True,
   'policy':'prevent_new_entries_only_keep_existing_exit_management'}
  if decision=='disarm_loss_limit':
   # Preserve existing positions and exit handling. Do not use stopped=true,
   # which would disable the existing automatic exit/recovery state machine.
   await c.execute("""UPDATE canary_control
     SET armed=false,problem='governor_7d_realized_loss_limit'
     WHERE id=1 AND armed=true""")
  await c.execute("INSERT INTO hive_governor_audit(seven_day_net_sol,trade_count,decision,details) VALUES($1,$2,$3,$4::jsonb)",net,n,decision,json.dumps(detail))
  return {'decision':decision,'trades':n,'net_sol':net,**detail}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

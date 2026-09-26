"""Persistent simulated/live-shaped execution accounting."""
import json
from db import connection
async def ensure_schema():
 async with connection() as c:
  await c.execute('''CREATE TABLE IF NOT EXISTS colony_execution_ledger(
   id BIGSERIAL PRIMARY KEY,intent_id TEXT UNIQUE NOT NULL,created_at TIMESTAMPTZ DEFAULT now(),
   run_id TEXT,mint TEXT,side TEXT,notional DOUBLE PRECISION,status TEXT NOT NULL,reason TEXT,
   quote JSONB,fill JSONB,entry_price DOUBLE PRECISION,mark_price DOUBLE PRECISION,
   gross_pnl DOUBLE PRECISION,friction_cost DOUBLE PRECISION,net_pnl DOUBLE PRECISION,
   mode TEXT NOT NULL DEFAULT 'simulated',broadcast BOOLEAN NOT NULL DEFAULT false,
   execution_reality JSONB,friction_ratio DOUBLE PRECISION,executable_edge_sol DOUBLE PRECISION)''')
  await c.execute("ALTER TABLE colony_execution_ledger ADD COLUMN IF NOT EXISTS execution_reality JSONB")
  await c.execute("ALTER TABLE colony_execution_ledger ADD COLUMN IF NOT EXISTS friction_ratio DOUBLE PRECISION")
  await c.execute("ALTER TABLE colony_execution_ledger ADD COLUMN IF NOT EXISTS executable_edge_sol DOUBLE PRECISION")
async def record(intent,result,quote=None,run_id=None):
 await ensure_schema()
 async with connection() as c:
  return await c.fetchval('''INSERT INTO colony_execution_ledger(intent_id,run_id,mint,side,notional,status,reason,quote,mode,broadcast)
   VALUES($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9,$10) ON CONFLICT(intent_id) DO NOTHING RETURNING id''',
   intent['intent_id'],run_id,intent['mint'],intent['side'],float(intent['notional']),
   'accepted' if result.get('accepted') else 'rejected',result.get('reason'),json.dumps(quote or {}),result.get('mode','simulated'),bool(result.get('broadcast',False)))
async def mark(intent_id,entry_price,mark_price,friction_cost=0.0):
 async with connection() as c:
  r=await c.fetchrow('SELECT side,notional FROM colony_execution_ledger WHERE intent_id=$1',intent_id)
  if not r:return None
  direction=1 if r['side']=='buy' else -1
  gross=float(r['notional'])*direction*(float(mark_price)/float(entry_price)-1)
  net=gross-float(friction_cost)
  await c.execute('''UPDATE colony_execution_ledger SET entry_price=$2,mark_price=$3,gross_pnl=$4,friction_cost=$5,net_pnl=$6 WHERE intent_id=$1''',intent_id,float(entry_price),float(mark_price),gross,float(friction_cost),net)
  return {'gross_pnl':gross,'friction_cost':float(friction_cost),'net_pnl':net}
async def summary(run_id=None):
 async with connection() as c:
  where='WHERE run_id=$1' if run_id else ''; args=[run_id] if run_id else []
  r=await c.fetchrow(f'''SELECT count(*) n,count(*) FILTER(WHERE status='accepted') accepted,
   count(*) FILTER(WHERE status='rejected') rejected,coalesce(sum(net_pnl),0) net_pnl,
   avg(net_pnl) FILTER(WHERE net_pnl IS NOT NULL) avg_net FROM colony_execution_ledger {where}''',*args)
  return dict(r)

async def record_reality(intent_id,reality,friction_cost=0.0):
 import json
 async with connection() as c:
  r=await c.fetchrow('SELECT notional FROM colony_execution_ledger WHERE intent_id=$1',intent_id)
  if not r:return
  n=float(r['notional'] or 0); edge=reality.get('gross_edge_sol') if reality.get('ok') else None
  ratio=(float(friction_cost)/n if n else None)
  await c.execute('UPDATE colony_execution_ledger SET execution_reality=$2::jsonb,friction_ratio=$3,executable_edge_sol=$4 WHERE intent_id=$1',intent_id,json.dumps(reality),ratio,edge)

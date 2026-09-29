"""Periodic independent audit + shadow-canary rehearsal. Read-only except audit snapshots."""
import asyncio,json,logging
from db import init_db,connection
from colony.independent_auditor import audit
from colony.reality_audit import reversal
from colony.shadow_canary import run as canary_run
from colony.paired_controls import collect as controls_collect
from colony.canary_gate import status as canary_gate_status
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

async def ensure(c):
    await c.execute('''CREATE TABLE IF NOT EXISTS colony_audit_snapshots(
      id BIGSERIAL PRIMARY KEY,observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      auditor JSONB NOT NULL,reversal JSONB NOT NULL,canary JSONB NOT NULL)''')

async def cycle():
    a=await audit(); r=await reversal(); r.pop('curve',None); can=await canary_run(); controls=await controls_collect(); gate=await canary_gate_status()
    async with connection() as c:
        await ensure(c); await c.execute('INSERT INTO colony_audit_snapshots(auditor,reversal,canary) VALUES($1::jsonb,$2::jsonb,$3::jsonb)',json.dumps(a),json.dumps(r,default=str),json.dumps(can))
    return {'faults':a['fault_count'],'reversal_net_gbp':r['net_gbp'],'canary':can,'controls':controls,'gate':gate}

async def main():
    await init_db()
    while True:
        try: logging.info('audit %s',await cycle())
        except Exception: logging.exception('audit_cycle_failed')
        await asyncio.sleep(900)
if __name__=='__main__': asyncio.run(main())

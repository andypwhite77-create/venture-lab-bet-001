"""Automate shadow snapshots, counterfactual breeding, replay and value audit."""
from db import connection
from colony.shadow_recorder import record
from colony.shadow_breeding import breed_plan
from colony.shadow_worker import process_shadow
from colony.shadow_replay import audit_plan
from colony.evolution_value import ledger

async def cycle(run_id):
    snap=await record(run_id)
    pid=snap.get('plan_id') if isinstance(snap,dict) else None
    if not pid:
        async with connection() as conn:
            pid=await conn.fetchval("SELECT id FROM colony_shadow_plans WHERE run_id=$1 ORDER BY id DESC LIMIT 1",run_id)
    reports=[]
    if pid:
        bred=await breed_plan(pid); audit=await audit_plan(pid); value=await ledger(pid)
        reports.append({'plan_id':pid,'bred':bred,'selection_audit':audit,'evolution_value':value})
    shadow=await process_shadow()
    return {'snapshot':snap,'shadow_entries':shadow,'plans':reports}

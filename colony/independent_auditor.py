"""Independent read-only auditor. Recomputes money from immutable ledger fields.
No Queen fitness, selection or promotion code is imported here.
"""
import math
from db import connection

TOL=1e-9

def recompute(row):
    if row['entry_price'] is None or row['mark_price'] is None: return None
    entry=float(row['entry_price']); mark=float(row['mark_price']); n=float(row['notional'] or 0)
    if entry<=0 or n<0 or not math.isfinite(entry+mark+n): return {'fault':'invalid_numeric'}
    direction=1 if row['side']=='buy' else -1
    gross=n*direction*(mark/entry-1)
    friction=float(row['friction_cost'] or 0); net=gross-friction
    return {'gross':gross,'net':net,'friction':friction}

async def audit(run_id=None):
    async with connection() as c:
        where='WHERE run_id=$1' if run_id else ''; args=[run_id] if run_id else []
        rows=await c.fetch(f'''SELECT id,intent_id,run_id,mint,side,notional,status,quote,entry_price,mark_price,
          gross_pnl,friction_cost,net_pnl,broadcast,created_at FROM colony_execution_ledger {where} ORDER BY id''',*args)
    faults=[]; recomputed_net=0.0; marked=0
    for r in rows:
        x=recompute(r)
        if not x: continue
        marked+=1
        if 'fault' in x: faults.append({'intent_id':r['intent_id'],'fault':x['fault']}); continue
        recomputed_net+=x['net']
        if r['gross_pnl'] is None or abs(float(r['gross_pnl'])-x['gross'])>TOL: faults.append({'intent_id':r['intent_id'],'fault':'gross_mismatch'})
        if r['net_pnl'] is None or abs(float(r['net_pnl'])-x['net'])>TOL: faults.append({'intent_id':r['intent_id'],'fault':'net_mismatch'})
        if float(r['friction_cost'] or 0)<0: faults.append({'intent_id':r['intent_id'],'fault':'negative_friction'})
        if r['broadcast']: faults.append({'intent_id':r['intent_id'],'fault':'unexpected_broadcast'})
    return {'rows':len(rows),'marked':marked,'recomputed_net':recomputed_net,'fault_count':len(faults),'faults':faults[:100],
            'basis':'ledger-only independent recomputation; no Queen/fitness imports'}

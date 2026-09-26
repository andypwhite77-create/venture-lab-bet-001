"""Prospective audit of shadow selection decisions using only later candidates."""
import json
from db import connection

async def audit_plan(plan_id):
    async with connection() as conn:
        p=await conn.fetchrow("SELECT * FROM colony_shadow_plans WHERE id=$1",plan_id)
        if not p:return {'status':'missing_plan'}
        plan=p['plan'] if isinstance(p['plan'],dict) else json.loads(p['plan'])
        cut=int(p['evidence_cutoff'] or 0); rejected=set(plan.get('replace',[]))
        rows=await conn.fetch("""SELECT e.genome_id,e.mint,o.net_return_pct FROM colony_forward_entries e
          JOIN LATERAL (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=e.candidate_id
          ORDER BY abs(horizon_minutes-e.hold_minutes) LIMIT 1) o ON true
          WHERE e.run_id=$1 AND e.candidate_id>$2""",p['run_id'],cut)
        future={}
        for r in rows: future.setdefault(r['genome_id'],{}).setdefault(r['mint'],float(r['net_return_pct']))
        def stats(ids):
            vals=[v for gid in ids for v in future.get(gid,{}).values()]
            return {'ants_with_future':sum(bool(future.get(g)) for g in ids),'trades':len(vals),
                    'mean_return_pct':round(sum(vals)/len(vals),4) if vals else None}
        all_ids=set(future); kept=all_ids-rejected
        culled=stats(rejected); survivors=stats(kept)
        edge=None
        if culled['mean_return_pct'] is not None and survivors['mean_return_pct'] is not None:
            edge=round(survivors['mean_return_pct']-culled['mean_return_pct'],4)
        return {'status':'prospective','plan_id':plan_id,'cutoff':cut,'future_rows':len(rows),
                'would_cull':culled,'would_keep':survivors,'selection_future_edge_pct':edge,
                'interpretation':'positive edge means shadow selection correctly preferred future survivors'}

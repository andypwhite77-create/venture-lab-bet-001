"""Prospective ledger: did counterfactual evolution add value after birth?"""
from db import connection

async def ledger(plan_id):
    async with connection() as conn:
        p=await conn.fetchrow("SELECT run_id,evidence_cutoff FROM colony_shadow_plans WHERE id=$1",plan_id)
        if not p:return {'status':'missing_plan'}
        kids=await conn.fetch("SELECT id,genome_id,parent_ids FROM colony_shadow_descendants WHERE shadow_plan_id=$1",plan_id)
        if not kids:return {'status':'waiting_for_breeders','plan_id':plan_id}
        def mean(rows):
            vals=[float(r['net_return_pct']) for r in rows]
            return (sum(vals)/len(vals),len(vals)) if vals else (None,0)
        child=await conn.fetch("""SELECT o.net_return_pct FROM colony_shadow_entries e JOIN LATERAL
          (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=e.candidate_id ORDER BY abs(horizon_minutes-e.hold_minutes) LIMIT 1) o ON true
          WHERE e.shadow_descendant_id=ANY($1::bigint[])""",[k['id'] for k in kids])
        parent_ids=[x for k in kids for x in k['parent_ids']]
        parents=await conn.fetch("""SELECT o.net_return_pct FROM colony_forward_entries e JOIN LATERAL
          (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=e.candidate_id ORDER BY abs(horizon_minutes-e.hold_minutes) LIMIT 1) o ON true
          WHERE e.run_id=$1 AND e.candidate_id>$2 AND e.genome_id=ANY($3::text[])""",p['run_id'],p['evidence_cutoff'],parent_ids)
        frozen=await conn.fetch("""SELECT o.net_return_pct FROM colony_forward_entries e JOIN LATERAL
          (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=e.candidate_id ORDER BY abs(horizon_minutes-e.hold_minutes) LIMIT 1) o ON true
          WHERE e.run_id=$1 AND e.candidate_id>$2""",p['run_id'],p['evidence_cutoff'])
        cm,cn=mean(child); pm,pn=mean(parents); fm,fn=mean(frozen)
        edge_parent=round(cm-pm,4) if cm is not None and pm is not None else None
        edge_frozen=round(cm-fm,4) if cm is not None and fm is not None else None
        return {'status':'prospective','plan_id':plan_id,'children':len(kids),
          'child_mean_pct':cm,'child_n':cn,'parent_mean_pct':pm,'parent_n':pn,
          'frozen_mean_pct':fm,'frozen_n':fn,'edge_vs_parent_pct':edge_parent,
          'edge_vs_frozen_pct':edge_frozen}

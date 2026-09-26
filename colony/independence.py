"""Opportunity-level evidence: prevents 100 ants voting 100x on one token."""
from db import connection

async def opportunity_report(run_id):
    async with connection() as conn:
        rows=await conn.fetch("""WITH e AS (
          SELECT mint, avg(o.net_return_pct) ret, count(DISTINCT genome_id) ants
          FROM colony_forward_entries f JOIN LATERAL (
            SELECT net_return_pct FROM research_outcomes
            WHERE candidate_id=f.candidate_id ORDER BY abs(horizon_minutes-f.hold_minutes) LIMIT 1
          ) o ON true WHERE f.run_id=$1 GROUP BY mint),
        b AS (SELECT mint, avg(o.net_return_pct) ret, count(DISTINCT genome_id) ants
          FROM colony_control_entries f JOIN LATERAL (
            SELECT net_return_pct FROM research_outcomes
            WHERE candidate_id=f.candidate_id ORDER BY abs(horizon_minutes-f.hold_minutes) LIMIT 1
          ) o ON true WHERE split_part(f.control_id,':',1)=$1 AND split_part(f.control_id,':',2)='blind' GROUP BY mint)
          SELECT e.mint,e.ret evolved_return,b.ret blind_return,e.ants evolved_ants,b.ants blind_ants
          FROM e JOIN b USING(mint) ORDER BY e.mint""",run_id)
    edges=[float(r['evolved_return']-r['blind_return']) for r in rows]
    return {'comparable_mints':len(rows),'mean_opportunity_edge_pct':sum(edges)/len(edges) if edges else None,
            'wins':sum(x>0 for x in edges),'losses':sum(x<0 for x in edges),'ties':sum(x==0 for x in edges)}

"""Read-only Canary consideration review: no promotion or execution authority.
One earliest entry per genome/mint, one eligible horizon outcome per entry.
Spartan results never treated as independent forward qualification.
"""
import asyncio,json,statistics
from db import init_db,connection

SQL="""WITH source AS (
 SELECT 'champion_paper' source,genome_id,mint,candidate_id,observed_at,hold_minutes FROM champion_paper_entries
 UNION ALL
 SELECT 'spartan_alumni' source,genome_id,mint,candidate_id,observed_at,hold_minutes FROM spartan_alumni_entries
), first_signal AS (
 SELECT DISTINCT ON(source,genome_id,mint) * FROM source
 ORDER BY source,genome_id,mint,observed_at,candidate_id
), observed AS (
 SELECT f.*,o.net_return_pct,o.raw_return_pct, o.measured_at FROM first_signal f
 LEFT JOIN LATERAL (
 SELECT net_return_pct,raw_return_pct,measured_at FROM research_outcomes o
 WHERE o.candidate_id=f.candidate_id AND o.horizon_minutes=f.hold_minutes
 AND o.measured_at>=f.observed_at+f.hold_minutes*interval '1 minute'
 AND o.net_return_pct IS NOT NULL ORDER BY o.measured_at ASC,o.id ASC LIMIT 1
 ) o ON TRUE
)
SELECT source,genome_id,count(*)::int distinct_mints,
 count(net_return_pct)::int completed,
 count(*) FILTER (WHERE net_return_pct IS NULL)::int pending,
 round(avg(net_return_pct)::numeric,3) mean_mark_pct,
 round(avg(least(net_return_pct,30))::numeric,3) capped_mean_pct,
 round(percentile_cont(0.5) WITHIN GROUP (ORDER BY net_return_pct)::numeric,3) median_mark_pct,
 round(min(net_return_pct)::numeric,3) worst_mark_pct,
 count(*) FILTER (WHERE net_return_pct < -20)::int severe_losses,
 count(*) FILTER (WHERE net_return_pct>0)::int wins,
 count(*) FILTER (WHERE raw_return_pct < -100 OR raw_return_pct > 500)::int suspect_marks,
 count(*) FILTER (WHERE net_return_pct < -100)::int fee_exceeds_stake_marks,
 max(observed_at) newest_signal
FROM observed GROUP BY source,genome_id ORDER BY completed DESC"""

def assess(r):
 n=r['completed'];mean=float(r['mean_mark_pct'] or 0);median=float(r['median_mark_pct'] or 0)
 worst=float(r['worst_mark_pct'] or 0);mints=r['distinct_mints'];loss=r['severe_losses']
 blockers=[]
 if n<25:blockers.append('less_than_25_distinct_completed_mints')
 if mean<=1: blockers.append('insufficient_mean_margin_for_execution_uncertainty')
 if float(r['capped_mean_pct'] or 0)<=1: blockers.append('capped_return_not_economically_positive')
 if median<=0:blockers.append('nonpositive_median')
 if worst < -20 or loss:blockers.append('severe_loss_tail')
 if r['suspect_marks']:blockers.append('implausible_raw_return_requires_quote_audit')
 blockers.append('no_independent_executable_forward_validation')
 return {**dict(r),'mean_mark_pct':mean,'capped_mean_pct':float(r['capped_mean_pct'] or 0),'median_mark_pct':median,'worst_mark_pct':worst,
  'tier':('research_shortlist' if len(blockers)==1 else 'research_repair'),
  'blockers':blockers,'authority':'read_only_no_promotion'}

async def run():
 await init_db()
 async with connection() as c:
  rows=await c.fetch(SQL)
 out=[assess(x) for x in rows]
 shortlist=sorted([x for x in out if x['tier']=='research_shortlist'],key=lambda x:(x['mean_mark_pct'],x['completed']),reverse=True)
 near=sorted([x for x in out if x['completed']>=25],key=lambda x:(x['capped_mean_pct'],x['median_mark_pct']),reverse=True)
 return {'surveyed_genomes':len(out),'research_shortlist_count':len(shortlist),'research_shortlist':shortlist[:12],
  'top_25_mint_diagnostics':near[:12], 'minimum_unique_mints':25,
  'integrity_policy':'Raw unleveraged returns below -100% are invalid. Net returns below -100% can arise after external fees and indicate economic catastrophe, not necessarily corruption. Independently audit extreme positive raw prices.',
  'rule':'Never promote from this review: sampled market marks are not executable fills, and qualification requires separate forward stress/Spartan checks.'}
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str))

"""Read-only, shared-candidate comparison; refuses to call unlike horizons an equal exam."""
import asyncio,json,statistics
from db import init_db,connection
SQL='''WITH old AS (
 SELECT DISTINCT ON(e.candidate_id) e.candidate_id,e.genome_id,e.hold_minutes,
 o.net_return_pct older_return
 FROM reversal_tournament_entries e
 JOIN reversal_tournament_ants a ON a.run_id=e.run_id AND a.genome_id=e.genome_id
 LEFT JOIN research_outcomes o ON o.candidate_id=e.candidate_id AND o.horizon_minutes=e.hold_minutes
 WHERE a.baseline=true
 ORDER BY e.candidate_id,e.observed_at,e.id
), newer AS (
 SELECT DISTINCT ON(e.candidate_id) e.candidate_id,e.genome_id,e.hold_minutes,
 l.net_return_pct newer_return, e.stake_gbp
 FROM eve_reference_paper_entries e
 LEFT JOIN controlled_paper_trade_ledger l ON l.entry_id=e.id
 ORDER BY e.candidate_id,e.observed_at,e.id
)
SELECT old.*,newer.genome_id newer_genome,newer.hold_minutes newer_horizon,
 newer.newer_return,newer.stake_gbp FROM old JOIN newer USING(candidate_id)
'''
def audit(rows):
 items=[dict(r) for r in rows]
 aligned=[x for x in items if x['hold_minutes']==x['newer_horizon'] and x['older_return'] is not None and x['newer_return'] is not None]
 def stats(key):
  vals=[float(x[key]) for x in aligned]
  return {'count':len(vals),'median_net_mark_pct':round(statistics.median(vals),3) if vals else None,
   'mean_net_mark_pct':round(statistics.mean(vals),3) if vals else None,
   'losing_fraction':round(sum(v<0 for v in vals)/len(vals),3) if vals else None}
 return {'shared_candidates':len(items),'equal_horizon_marked_pairs':len(aligned),
  'older_baseline':stats('older_return'),'newer_reference':stats('newer_return'),
  'excluded_for_horizon_or_missing_mark':len(items)-len(aligned),
  'interpretation':'Diagnostic only: older and newer values may use different cost assumptions, genome selection and observation timing. Not an identical-genome replay or executable fill comparison.',
  'authority':'read_only_no_breeding_no_trading'}
async def run():
 await init_db()
 async with connection() as c:rows=await c.fetch(SQL)
 return audit(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

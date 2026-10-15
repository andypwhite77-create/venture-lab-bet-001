"""Full available eligible reference-history replay for fixed plasticity policy.
No historical data is treated as forward evidence or live qualification.
"""
import asyncio,json
from db import init_db,connection
from colony.ant_plasticity_shadow import evaluate

async def run():
 await init_db()
 async with connection() as c:
  coverage=await c.fetchrow("SELECT count(*)::int candidate_count,min(created_at) oldest,max(created_at) newest FROM research_candidates")
  entries=await c.fetch("""SELECT e.id entry_id,e.genome_id,e.observed_at,r.features
   FROM eve_reference_paper_entries e JOIN research_candidates r ON r.id=e.candidate_id
   JOIN controlled_paper_cohort cohort ON cohort.genome_id=e.genome_id
   WHERE cohort.status='observation_only' AND e.observed_at>=cohort.started_at
   ORDER BY e.observed_at,e.id""")
  marks=await c.fetch("""SELECT l.entry_id,l.genome_id,l.outcome_at,l.net_return_pct net_pct,l.paper_pnl_gbp
   FROM controlled_paper_trade_ledger l JOIN controlled_paper_cohort cohort ON cohort.genome_id=l.genome_id
   WHERE cohort.status='observation_only' ORDER BY l.outcome_at,l.entry_id""")
  by={};results={}
  for m in marks:
   by.setdefault(m['genome_id'],[]).append(dict(m));results[m['entry_id']]=float(m['paper_pnl_gbp'])
  choices=evaluate([dict(e) for e in entries],by)
  observed=[x for x in choices if x['entry_id'] in results]
  filtered=[x for x in observed if x['shadow_action']=='follow_dna']
  return {'source_market_candidates':coverage['candidate_count'],
   'source_start':coverage['oldest'].isoformat() if coverage['oldest'] else None,
   'source_end':coverage['newest'].isoformat() if coverage['newest'] else None,
   'eligible_reference_entries':len(entries),'marked_comparable_entries':len(observed),
   'unmarked_entries':len(entries)-len(observed),
   'fixed_dna_nominal_pnl_gbp':round(sum(results[x['entry_id']] for x in observed),3),
   'adaptive_nominal_pnl_gbp':round(sum(results[x['entry_id']] for x in filtered),3),
   'marked_abstentions':len(observed)-len(filtered),
   'historical_coverage':'all_available_eligible_reference_entries_not_all_market_candidates',
   'status':'diagnostic_only_not_prospective_or_live_proof'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

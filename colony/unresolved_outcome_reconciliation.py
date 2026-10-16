"""Read-only reconciliation: distinguish unmarked research outcomes from exit quotes."""
import asyncio,json
from collections import Counter
from db import init_db,connection
from colony.shared_wallet_shadow import SQL,simulate
from colony.canary_quote_economics import evaluate

DETAIL="""SELECT e.id entry_id,e.candidate_id,e.hold_minutes,
 (SELECT count(*) FROM research_outcomes o WHERE o.candidate_id=e.candidate_id AND o.horizon_minutes=e.hold_minutes) matching_horizon_outcomes,
 (SELECT count(*) FROM research_outcomes o WHERE o.candidate_id=e.candidate_id AND o.horizon_minutes=e.hold_minutes AND o.measured_at>=e.observed_at+e.hold_minutes*interval '1 minute' AND o.raw_return_pct IS NOT NULL) eligible_outcomes,
 a.quote entry_quote,b.quote exit_quote,a.latency_seconds entry_latency,b.latency_seconds exit_latency
 FROM eve_reference_paper_entries e
 LEFT JOIN controlled_paper_trade_ledger l ON l.entry_id=e.id
 LEFT JOIN canary_forward_quote_observations a ON a.entry_id=e.id AND a.phase='entry' AND a.status='quoted'
 LEFT JOIN canary_forward_quote_observations b ON b.entry_id=e.id AND b.phase='exit' AND b.status='quoted'
 WHERE l.entry_id IS NULL AND e.id=ANY($1::bigint[])"""
def explain(rows):
 out=[]
 for row in rows:
  r=dict(row)
  if int(r['eligible_outcomes'])>0:reason='eligible_outcome_exists_ledger_not_ingested'
  elif int(r['matching_horizon_outcomes'])>0:reason='outcome_exists_but_ineligible_time_or_return'
  else:reason='no_matching_horizon_research_outcome'
  quoted=evaluate([r]) if r.get('entry_quote') and r.get('exit_quote') else []
  out.append({'entry_id':r['entry_id'],'candidate_id':r['candidate_id'],'reason':reason,
   'matched_outcomes':int(r['matching_horizon_outcomes']),'eligible_outcomes':int(r['eligible_outcomes']),
   'paired_quote_only':bool(quoted),'indicative_quote_pct':quoted[0]['net_pct'] if quoted else None,
   'quote_is_not_research_outcome':True})
 return {'positions':out,'reasons':dict(Counter(x['reason'] for x in out)),
 'authority':'research_read_only_no_ledger_mutation_no_fake_fills'}
async def run():
 await init_db()
 async with connection() as c:
  records=await c.fetch(SQL)
  wallet=simulate(records)
  ids=sorted({p['entry_id'] for v in wallet['results'].values() for p in v['unresolved']['positions']})
  details=await c.fetch(DETAIL,ids)
 return {'wallet_unresolved_by_policy':{k:v['unresolved'] for k,v in wallet['results'].items()},'reconciliation':explain(details)}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

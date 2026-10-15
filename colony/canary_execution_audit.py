"""Audit sampled winner marks for entry liquidity and contemporaneous execution evidence.
Research-only: no old quote is assumed executable at the strategy's exit horizon.
"""
import asyncio,json
from db import init_db,connection
SQL="""SELECT o.id outcome_id,o.candidate_id,o.horizon_minutes,o.raw_return_pct,o.net_return_pct,
 c.created_at,c.mint,c.features->>'liquidity_usd' entry_liquidity_usd,
 (SELECT count(*) FROM research_price_path p WHERE p.candidate_id=c.id)::int path_samples,
 (SELECT count(*) FROM colony_execution_ledger x WHERE
   (x.quote->'attribution'->>'candidate_id')=c.id::text)::int entry_execution_checks
 FROM research_outcomes o JOIN research_candidates c ON c.id=o.candidate_id
 WHERE o.raw_return_pct>500 ORDER BY o.raw_return_pct DESC"""
def audit(rows):
 out={'extreme_outcomes':len(rows),'distinct_candidates':len(set(r['candidate_id'] for r in rows)),
      'missing_entry_liquidity':0,'thin_entry_liquidity_under_25000':0,
      'without_price_path':0,'without_attributed_execution_check':0,'verifiable_exit_quotes':0}
 samples=[]
 for r in rows:
  try:liquidity=float(r['entry_liquidity_usd'])
  except (ValueError,TypeError):liquidity=None
  if liquidity is None:out['missing_entry_liquidity']+=1
  elif liquidity<25000:out['thin_entry_liquidity_under_25000']+=1
  if not r['path_samples']:out['without_price_path']+=1
  if not r['entry_execution_checks']:out['without_attributed_execution_check']+=1
  # Entry-only observations do not establish exit-side liquidity or realised fills.
  if len(samples)<8:samples.append({'candidate_id':r['candidate_id'],'raw_return_pct':round(float(r['raw_return_pct']),2),
    'entry_liquidity_usd':liquidity,'price_path_samples':r['path_samples'],
    'entry_execution_checks':r['entry_execution_checks'],'exit_executable':False})
 return {**out,'largest_examples':samples,'qualification':'unverified_no_historical_exit_quote_proof',
  'authority':'research_only_no_promotion_no_live'}
async def run():
 await init_db()
 async with connection() as c: rows=await c.fetch(SQL)
 return audit(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

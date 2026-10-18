"""Read-only visibility into the frozen prospective exit trial admission pipeline."""
import asyncio,json
from db import init_db,connection
from colony.prospective_exit_trial import TRIAL

async def run():
 await init_db()
 async with connection() as c:
  trial=await c.fetchrow('SELECT started_at,hold_minutes FROM prospective_exit_trials WHERE trial=$1',TRIAL)
  if not trial:return {'status':'trial_not_registered','authority':'diagnostic_only'}
  candidates=await c.fetch('''SELECT r.id,r.created_at,r.entry_price,r.market,
   t.candidate_id IS NOT NULL processed,
   (r.created_at <= now()-interval '90 minutes') mature,
   (SELECT count(*) FROM research_price_path p WHERE p.candidate_id=r.id
      AND p.quality='fresh_fetch' AND p.observed_at>=r.created_at
      AND p.observed_at<r.created_at+interval '60 minutes') samples
   FROM research_candidates r
   LEFT JOIN prospective_exit_trial_results t ON t.candidate_id=r.id AND t.trial=$1
   WHERE r.created_at >= $2 ORDER BY r.id''',TRIAL,trial['started_at'])
  counts={'total':len(candidates),'awaiting_maturity':0,'mature_unprocessed':0,'processed':0,'unverified_entry':0,'no_path_samples':0,'mature_with_samples':0}
  for cnd in candidates:
   market=cnd['market'];market=json.loads(market) if isinstance(market,str) else dict(market or {})
   if not cnd['entry_price'] or market.get('price_evidence')=='discovery_only_no_provider_tick_timestamp':counts['unverified_entry']+=1
   if cnd['samples']==0:counts['no_path_samples']+=1
   if cnd['processed']:counts['processed']+=1
   elif cnd['mature']:
    counts['mature_unprocessed']+=1
    if cnd['samples']>0:counts['mature_with_samples']+=1
   else:counts['awaiting_maturity']+=1
  return {'trial':TRIAL,'started_at':trial['started_at'].isoformat(),'counts':counts,'authority':'read_only_diagnostic_not_fill_or_qualification'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

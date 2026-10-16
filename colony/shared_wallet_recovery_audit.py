"""Read-only unresolved wallet exposure and quote-evidence audit; never assumes liquidation."""
import asyncio,json
from collections import Counter
from datetime import datetime,timezone
from db import init_db,connection
from colony.shared_wallet_shadow import SQL,simulate

def review(rows,as_of=None):
 as_of=as_of or datetime.now(timezone.utc)
 records=[dict(r) for r in rows]
 wallet=simulate(records,as_of=as_of)
 lookup={r['entry_id']:r for r in records}
 reviewed={}
 for policy,v in wallet['results'].items():
  details=[]
  for p in v['unresolved']['positions']:
   r=lookup[p['entry_id']]
   entry=r.get('entry_status');exit=r.get('exit_status')
   if entry!='quoted':reason='entry_quote_unverified' if entry is None else 'entry_route_unavailable'
   elif exit=='unavailable':reason='exit_route_unavailable'
   elif exit=='quoted':reason='exit_quote_exists_but_paper_outcome_unresolved'
   else:reason='exit_quote_missing'
   details.append({'entry_id':p['entry_id'],'candidate_id':p['candidate_id'],
    'age_minutes':round((as_of-r['entry_at']).total_seconds()/60,1),
    'stake_gbp':p['stake_gbp'],'state':p['state'],'evidence':reason,
    'entry_latency_seconds':r.get('entry_latency'),'exit_latency_seconds':r.get('exit_latency')})
  counts=Counter(d['evidence'] for d in details)
  locked=sum(d['stake_gbp'] for d in details)
  reviewed[policy]={'positions':details,'reasons':dict(counts),'locked_gbp':round(locked,3),
   'haircut_scenarios_gbp':{str(h):round(locked*h/100,3) for h in (0,25,50,75,100)}}
 return {'wallet':wallet,'unresolved_review':reviewed,'authority':'read_only_hypothetical_no_liquidation',
  'warning':'Haircuts are assumed recovery fractions of historical stake, not Jupiter sale quotes. Missing market evidence is not proof of zero value.'}
async def run():
 await init_db()
 async with connection() as c:rows=await c.fetch(SQL)
 return review(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

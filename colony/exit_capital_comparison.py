"""Read-only equal-bankroll replay of FROZEN prospective sampled exit policies.
Not fills; excluded incomplete outcomes never become profits or freed capital.
"""
import asyncio,json
from collections import defaultdict
from datetime import datetime,timezone
from db import init_db,connection
from colony.prospective_exit_trial import TRIAL,POLICIES
START=0.1
STAKE=0.01

def compare(rows,as_of=None):
 as_of=as_of or datetime.now(timezone.utc)
 ordered=sorted((dict(r) for r in rows),key=lambda r:(r['entry_at'],r['candidate_id']))
 result={}
 for policy in POLICIES:
  available=START;locked=[];profit=0.;completed=blocked=excluded=0;duration_hours=0.;worst=0.
  for r in ordered:
   timestamp=r['entry_at'];pending=[]
   for end,proceeds,stake in locked:
    if end<=timestamp:available+=proceeds;profit+=proceeds-stake;completed+=1
    else:pending.append((end,proceeds,stake))
   locked=pending
   o=r['outcome'];o=json.loads(o) if isinstance(o,str) else o
   record=o.get(policy)
   if not all(isinstance(o.get(p),dict) and o[p].get('status')=='observed_path' for p in POLICIES):excluded+=1;continue
   if not record or record.get('status')!='observed_path':excluded+=1;continue
   if available+1e-12<STAKE:blocked+=1;continue
   end=datetime.fromisoformat(record['exit_at'])
   if end<timestamp:excluded+=1;continue
   return_pct=float(record['net_pct'])
   proceeds=STAKE*(1+return_pct/100)
   if proceeds<0:excluded+=1;continue
   available-=STAKE;locked.append((end,proceeds,STAKE));duration_hours+=(end-timestamp).total_seconds()/3600*STAKE
   worst=min(worst,return_pct)
  # Settle only observed exits that actually fall before the review time.
  pending=[]
  for end,proceeds,stake in locked:
   if end<=as_of:available+=proceeds;profit+=proceeds-stake;completed+=1
   else:pending.append((end,proceeds,stake))
  locked=pending
  result[policy]={'bankroll_sol':START,'free_sol':round(available,9),'locked_stake_sol':round(sum(x[2] for x in locked),9),'completed':completed,'blocked_insufficient_cash':blocked,'excluded_missing_path':excluded,'realized_hypothetical_net_sol':round(profit,9),'gross_reserved_sol_hours':round(duration_hours,8),'worst_sampled_net_pct':round(worst,4),'pending':len(locked),'qualified':False}
 return {'policies':result,'candidates':len(ordered),'authority':'matched_prospective_sampled_prices_no_fills_no_live','caveat':'No slippage or execution guarantee. Pending positions intentionally remain locked; results not qualification evidence.'}
async def run():
 await init_db()
 async with connection() as c:
  rows=await c.fetch('SELECT candidate_id,entry_at,outcome FROM prospective_exit_trial_results WHERE trial=$1 ORDER BY entry_at,candidate_id',TRIAL)
 return compare(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

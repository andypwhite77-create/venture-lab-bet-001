"""Paired forward sampled-mark outcomes on identical candidates (not fills)."""
import asyncio,json,statistics
from db import init_db,connection
from colony.prospective_exit_trial import TRIAL,POLICIES

def summarize(rows):
 valid=[];excluded=0
 for raw in rows:
  item=raw['outcome'];item=json.loads(item) if isinstance(item,str) else item
  if not all(isinstance(item.get(p),dict) and item[p].get('status')=='observed_path' for p in POLICIES):excluded+=1;continue
  valid.append(item)
 policies={}
 for name in POLICIES:
  returns=[float(x[name]['net_pct']) for x in valid]
  policies[name]={'sample_count':len(returns),'mean_sampled_net_pct':round(statistics.mean(returns),4) if returns else None,'median_sampled_net_pct':round(statistics.median(returns),4) if returns else None,'worst_sampled_net_pct':round(min(returns),4) if returns else None,'sampled_wins':sum(x>0 for x in returns)}
 control=[float(x['control']['net_pct']) for x in valid]
 for name in POLICIES:
  deltas=[float(x[name]['net_pct'])-c for x,c in zip(valid,control)]
  policies[name]['mean_paired_delta_pp']=round(statistics.mean(deltas),4) if deltas else None
 return {'paired_candidates':len(valid),'excluded':excluded,'policies':policies,'authority':'prospective_sampled_marks_not_executable_fills','limitation':'no funded-position selection; sample size and slippage may prevent generalization'}
async def run():
 await init_db()
 async with connection() as c:
  rows=await c.fetch('SELECT outcome FROM prospective_exit_trial_results WHERE trial=$1',TRIAL)
 return summarize(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

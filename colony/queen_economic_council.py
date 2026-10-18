"""Observation-only Queen Economic Council over registered prospective confirmations.
Equal nominal bankrolls; no fills, economic authority, breeding or promotion.
"""
import asyncio,json,statistics
from collections import defaultdict
from db import init_db,connection
from colony.queen_research_incentives import grade
START=0.1
STAKE=0.01
BASE_BUDGET=2

def evaluate(confirmations,observations,hypotheses):
 by_id={int(x['id']):dict(x) for x in confirmations}
 grouped=defaultdict(list)
 for raw in observations:
  x=dict(raw);cid=int(x['confirmation_id'])
  if cid in by_id:grouped[cid].append(x)
 credits=defaultdict(lambda:{'tests':0,'historical_flags':0})
 for raw in hypotheses:
  h=dict(raw);result=h['result'];result=json.loads(result) if isinstance(result,str) else result
  credits[h['queen']]['tests']+=1;credits[h['queen']]['historical_flags']+=grade(result)['credit']
 reports=[]
 for cid,conf in sorted(by_id.items()):
  candidates=sorted(grouped[cid],key=lambda x:(x['observed_at'],x['candidate_id']))
  valid=[x for x in candidates if x['selected'] is not None and x['net_pct'] is not None]
  selected=[float(x['net_pct']) for x in valid if x['selected']]
  controls=[float(x['net_pct']) for x in valid if not x['selected']]
  # No outcome at all is a success; merely observing a favourable mark is not a fill.
  mean=lambda a:round(statistics.mean(a),4) if a else None
  eligible=len(selected)>=25 and len(controls)>=25 and len(set(x['candidate_id'] for x in valid))>=50
  uplift=mean(selected)-mean(controls) if eligible else None
  reports.append({'confirmation_id':cid,'queen':conf['queen'],'observed':len(candidates),'matched_feature_known':len(valid),
    'selected_n':len(selected),'other_n':len(controls),'selected_mean_mark_pct':mean(selected),
    'other_mean_mark_pct':mean(controls),'worst_selected_mark_pct':round(min(selected),4) if selected else None,
    'descriptive_uplift_pp':round(uplift,4) if uplift is not None else None,
    'equal_reference_bankroll_sol':START,'reference_stake_sol':STAKE,
    'earned_economic_reward':None,'ready_for_economic_comparison':eligible,
    'missing_or_invalid_feature_rows':len(candidates)-len(valid),'authority':'observational_only_no_capital_replay'})
 queens={}
 for queen in sorted({x['queen'] for x in confirmations}|set(credits)):
  c=credits[queen];queen_reports=[r for r in reports if r['queen']==queen]
  queens[queen]={'historical_attempts':c['tests'],'historical_consistency_flags':c['historical_flags'],
   'registered_forward_trials':len(queen_reports),'reference_bankroll_sol':START,
   'research_budget_remaining':max(0,BASE_BUDGET-min(c['tests'],BASE_BUDGET)),
   'economic_reward':None,'promotion_allowed':False}
 return {'queens':queens,'forward_trials':reports,'authority':'read_only_economic_council','limitations':'Equal reference bankrolls are comparison labels, not transactional simulation; no real costs, fills or capital recycling proven. Historical flags never add to economic reward.'}
async def run():
 await init_db()
 async with connection() as c:
  confirmations=await c.fetch('SELECT id,queen FROM queen_forward_confirmations')
  observations=await c.fetch('SELECT confirmation_id,candidate_id,observed_at,selected,net_pct FROM queen_forward_confirmation_results')
  history=await c.fetch('SELECT queen,result FROM queen_historical_hypotheses')
 return evaluate(confirmations,observations,history)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

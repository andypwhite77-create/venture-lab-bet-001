"""Read-only comparison of simple founder mechanisms on identical market partitions.
No promotion, spawning, holdout-driven selection, or trade authority.
"""
import asyncio,json
from db import init_db,connection
from colony.historical_nursery import founders,load_rows,split_rows,evaluate
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate

def verdict(train,validation):
 if min(train.get('n',0),validation.get('n',0))<25:return 'insufficient_distinct_mints'
 if min(float(train.get('avg_net_gbp') or -1),float(validation.get('avg_net_gbp') or -1))<=0:return 'negative_after_cost_economics'
 if min(float(train.get('median_return_pct') or -100),float(validation.get('median_return_pct') or -100))<=0:return 'negative_typical_trade'
 if min(float(train.get('worst_return_pct') or -100),float(validation.get('worst_return_pct') or -100))< -25:return 'severe_downside'
 return 'research_candidate_only_requires_independent_validation'

async def run():
 await init_db()
 async with connection() as c:
  rows=await load_rows(c)
  fee=await measured_roundtrip_network_fee_sol(c);rate,_=sol_gbp_rate();cost=fee*rate
 splits=split_rows(rows)
 report=[]
 for name,g in founders().items():
  parts=[evaluate(g,s,TARGET_STAKE_GBP,cost) for s in splits[:2]]
  t,v=parts
  report.append({'mechanism':name,'train_mints':t.get('n',0),'validation_mints':v.get('n',0),
    'train_net_gbp_per_trade':t.get('avg_net_gbp'),'validation_net_gbp_per_trade':v.get('avg_net_gbp'),
    'train_median_pct':t.get('median_return_pct'),'validation_median_pct':v.get('median_return_pct'),
    'validation_worst_pct':v.get('worst_return_pct'),'diagnosis':verdict(t,v)})
 return {'historical_market_rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),
         'test_partitions':'mint-isolated chronological train and validation, holdout not examined',
         'mechanisms':report,'promotion_allowed':False,'paper_admission_allowed':False}
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str))

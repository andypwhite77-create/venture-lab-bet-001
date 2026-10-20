"""Evidence-led research allocator. No deployment, promotion or execution authority.
Maintains hypotheses and allocates investigation based on train/validation economics.
"""
import asyncio,json
from db import init_db,connection
from colony.simple_mechanism_audit import run as audit_mechanisms

SCHEMA='''CREATE TABLE IF NOT EXISTS queen_research_director_decisions
(id bigserial primary key, created_at timestamptz not null default clock_timestamp(),
 report jsonb not null);'''

def allocate(audit):
 decisions=[]
 for m in audit['mechanisms']:
  name=m['mechanism'];n=min(m['train_mints'],m['validation_mints'])
  train=m['train_net_gbp_per_trade'];val=m['validation_net_gbp_per_trade']
  median=min(m['train_median_pct'] or -100,m['validation_median_pct'] or -100)
  if n<25:action='collect_distinct_evidence';priority=1
  elif train is None or val is None:action='repair_evidence';priority=1
  elif train>0 and val>0 and median>0:action='investigate_exit_robustness';priority=4
  elif train>0 and val>0:action='investigate_loss_tail_and_typical_trade';priority=3
  elif val>0:action='investigate_regime_shift';priority=2
  else:action='retire_current_founder_test_new_mechanism';priority=0
  decisions.append({'family':name,'action':action,'priority':priority,'reason':m['diagnosis'],
   'train_net_gbp':train,'validation_net_gbp':val,'train_mints':m['train_mints'],
   'validation_mints':m['validation_mints'],'breeding_authorized':False})
 return sorted(decisions,key=lambda x:(-x['priority'],x['family']))

async def run():
 audit=await audit_mechanisms()
 allocations=allocate(audit)
 report={'data_mints':audit['unique_mints'],'allocations':allocations,'holdout_untouched':True,
         'authority':'research_priorities_only','breeding_authorized':False,
         'paper_authorized':False,'live_authorized':False}
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  await c.execute('INSERT INTO queen_research_director_decisions(report) VALUES($1::jsonb)',json.dumps(report))
 return report
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str))

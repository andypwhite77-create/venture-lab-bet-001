"""Bounded independent paper exploration, not Reversal qualification or breeding.
Distinct observable entry hypotheses; frozen comparison without live authority.
"""
import asyncio,json
from db import init_db,connection
from colony.genome import genome_id

RUN='reversal-novelty-study-v1'
# These are deliberately distinct entry mechanisms, not cosmetic exit variations.
HYPOTHESES=(
 ('oversold_rebound',{'price_change_m5':{'max':-5},'dex_buy_ratio_m5':{'min':0.55}}),
 ('buyers_absorb_selloff',{'price_change_m5':{'max':-2},'buy_acceleration':{'min':1.5}}),
 ('low_liquidity_reversal',{'price_change_m5':{'max':-3},'volume_liquidity_m5':{'min':0.08}}),
 ('flow_reversal',{'flow_shift':{'min':0.2},'price_change_m5':{'max':-2}}),
)
def frozen_agents():
 agents=[]
 # Shared baseline is an entry-eligible diagnostic, not an expert or a winner.
 defs=[('observation_control',{'price_change_m5':{'max':-2}})]+list(HYPOTHESES)
 for name,predicates in defs:
  genome={'family':'reversal_exploration','species':name,'predicates':predicates,
    'parameters':{'hold_minutes':15,'stop_loss_pct':None,'take_profit_pct':None},
    'bounds':{},'research_only':True}
  agents.append((genome,name=='observation_control'))
 assert len({genome_id(x) for x,_ in agents})==len(agents)
 return agents
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(open('/app/colony/family_tournament_schema.sql').read())
  if await c.fetchval('SELECT 1 FROM family_tournament_runs WHERE run_id=$1',RUN):
   return {'status':'already_registered','run_id':RUN}
  agents=frozen_agents()
  async with c.transaction():
   await c.execute("""INSERT INTO family_tournament_runs(run_id,family,status,stage_size,config)
    VALUES($1,'reversal_exploration','collecting',$2,$3::jsonb)""",RUN,len(agents),
    json.dumps({'mode':'forward_shadow_paired_frozen','research_only':True,
    'promotion_authority':False,'independent_hypotheses':[x for x,_ in HYPOTHESES],
    'do_not_feed_spartan_training':True}))
   for genome,control in agents:
    await c.execute("""INSERT INTO family_tournament_ants
      (run_id,genome_id,genome,cohort,baseline) VALUES($1,$2,$3::jsonb,$4,$5)""",
      RUN,genome_id(genome),json.dumps(genome),
      'observation_control' if control else 'quarantined_novelty',control)
 return {'status':'registered','run_id':RUN,'novel_hypotheses':len(agents)-1,'baseline':1}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

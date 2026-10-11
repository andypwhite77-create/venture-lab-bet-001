"""Freeze a bounded matched forward cohort from a Queen training-selected finalist.
No Spartan result or holdout outcome influences enrollment. Paper only.
"""
import asyncio,copy,json,random
from db import init_db,connection
from colony.genome import genome_id
from colony.queen_pattern_recognition import targeted_loss_challenger

def cohort(base,count=8):
 if not isinstance(base,dict) or not base.get('predicates'):raise ValueError('invalid_base')
 ctrl=copy.deepcopy(base);ctrl['species']='loss_tail_control'
 out=[(ctrl,True)];seen={genome_id(ctrl)}
 for seed in range(1000):
  child=targeted_loss_challenger(base,random.Random(seed))
  key=genome_id(child)
  if key not in seen:seen.add(key);out.append((child,False))
  if len(out)>=count+1:break
 if len(out)<count+1:raise RuntimeError('insufficient_distinct_challengers')
 assert all(x['predicates']==base['predicates'] for x,_ in out)
 return out

async def run():
 await init_db()
 async with connection() as c:
  await c.execute(open('/app/colony/family_tournament_schema.sql').read())
  e=await c.fetchrow("SELECT id FROM hive_experiments WHERE kind='live_loss_asymmetry' AND status='awaiting_prospective_test' ORDER BY id DESC LIMIT 1")
  if not e:return {'status':'no_active_experiment'}
  run_id=f"hive-loss-tail-{e['id']}"
  existing=await c.fetchval('SELECT run_id FROM family_tournament_runs WHERE run_id=$1',run_id)
  if existing:return {'status':'already_enrolled','run_id':run_id}
  # Historical finalist rankings are based on train/validation; do not inspect holdout.
  r=await c.fetchrow("SELECT id,finalists FROM historical_nursery_runs WHERE family='queen_pattern' ORDER BY id DESC LIMIT 1")
  if not r:return {'status':'no_finalists'}
  items=r['finalists'];items=json.loads(items) if isinstance(items,str) else items
  base=next((x.get('genome') for x in items if isinstance(x.get('genome'),dict) and x['genome'].get('predicates')),None)
  if not base:return {'status':'no_usable_genome'}
  agents=cohort(base)
  async with c.transaction():
   await c.execute("""INSERT INTO family_tournament_runs(run_id,family,status,stage_size,config)
    VALUES($1,'queen_pattern','collecting',100,$2::jsonb)""",run_id,json.dumps({
    'experiment_id':e['id'],'source_nursery_run_id':r['id'],
    'mode':'forward_shadow_paired_frozen','qualifies_for_live':False,
    'parent_selection':'existing_finalist_no_holdout_selection'}))
   for i,(g,is_ctrl) in enumerate(agents):
    await c.execute("""INSERT INTO family_tournament_ants
      (run_id,genome_id,genome,cohort,baseline)
      VALUES($1,$2,$3::jsonb,$4,$5)""",
      run_id,genome_id(g),json.dumps(g),'unchanged_control' if is_ctrl else 'loss_tail_challenger',is_ctrl)
  return {'status':'enrolled','run_id':run_id,'control':1,'challengers':len(agents)-1,'source_nursery_run_id':r['id']}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

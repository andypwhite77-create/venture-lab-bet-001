import asyncio,json
from datetime import datetime,timezone
from db import init_db,connection
from colony.genome import genome_id
from colony.family_tournament import FAMILIES,make_population,founder,DEFAULT_SEED,STAGES
async def main():
 await init_db(); now=datetime.now(timezone.utc); made=[]
 async with connection() as c:
  for family in FAMILIES:
   existing=await c.fetchval("SELECT run_id FROM family_tournament_runs WHERE family=$1 AND status='collecting' ORDER BY created_at DESC LIMIT 1",family)
   if existing:made.append({'family':family,'run_id':existing,'existing':True});continue
   pop=make_population(family); run=f'{family}-tournament-'+now.strftime('%Y%m%dT%H%M%SZ')
   cfg={'seed':DEFAULT_SEED,'stages':STAGES,'baseline_immortal':True,'max_mutated_dimensions':2,'mode':'prospective_shadow_only'}
   await c.execute('INSERT INTO family_tournament_runs(run_id,family,config) VALUES($1,$2,$3::jsonb)',run,family,json.dumps(cfg))
   base=genome_id(founder(family))
   for i,g in enumerate(pop):
    cohort='baseline' if i==0 else g.get('tournament',{}).get('cohort','mixed')
    await c.execute('INSERT INTO family_tournament_ants(run_id,genome_id,genome,cohort,baseline) VALUES($1,$2,$3::jsonb,$4,$5)',run,genome_id(g),json.dumps(g),cohort,i==0)
   made.append({'family':family,'run_id':run,'ants':len(pop),'baseline':base})
 print(json.dumps(made,indent=2))
if __name__=='__main__':asyncio.run(main())

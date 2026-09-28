"""Create a separate 100-ant Reversal tournament without touching the frozen colony."""
import asyncio, json
from datetime import datetime, timezone
from db import init_db, connection
from colony.genome import genome_id
from colony.reversal_tournament import make_population, baseline_genome, DEFAULT_SEED

async def main():
    await init_db(); pop=make_population(100,DEFAULT_SEED); base_id=genome_id(baseline_genome())
    run_id='reversal-tournament-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    config={"seed":DEFAULT_SEED,"stages":[[100,20,60],[60,35,30],[30,40,15],[15,50,5],[5,25,5]],
            "baseline_immortal":True,"max_mutated_dimensions":2,"mode":"prospective_shadow_only"}
    async with connection() as c:
        await c.execute("INSERT INTO reversal_tournament_runs(run_id,config) VALUES($1,$2::jsonb)",run_id,json.dumps(config))
        for i,g in enumerate(pop):
            cohort='baseline' if i==0 else g.get('tournament',{}).get('cohort','mixed')
            await c.execute("""INSERT INTO reversal_tournament_ants(run_id,genome_id,genome,cohort,baseline)
              VALUES($1,$2,$3::jsonb,$4,$5)""",run_id,genome_id(g),json.dumps(g),cohort,i==0)
    print(json.dumps({"run_id":run_id,"ants":len(pop),"baseline":base_id,"seed":DEFAULT_SEED},indent=2))
if __name__=='__main__': asyncio.run(main())

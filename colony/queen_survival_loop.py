"""Persistent Queen discovery loop.
The Queen breeds on train+validation, then an external Spartan examiner audits frozen
finalists. Exact Spartan thresholds/results are not fed back into breeding.
"""
import asyncio,json,os,time
from db import init_db,connection
from colony.queen_pattern_recognition import run as queen_run
from colony.spartan_v2_runner import audit_family

STATE='/data/queen_survival_state.json'

def save_state(x):
    os.makedirs(os.path.dirname(STATE),exist_ok=True)
    with open(STATE,'w') as f: json.dump(x,f,indent=2)

async def main():
    await init_db(); campaign=0
    while True:
        campaign+=1
        async with connection() as c:
            print(json.dumps({'event':'campaign_start','campaign':campaign,'directive':'PERSIST ADAPT BREED KILL FRAGILITY'}),flush=True)
            summary,_=await queen_run(c,seed=300933+campaign,checkpoint='/data/queen_pattern_checkpoint.pkl')
            audit=await audit_family(c,'queen_pattern')
            passed=[x for x in audit['results'] if x['stress_pass']]
            distinct={tuple(x['events']) for x in passed}
            public={'campaign':campaign,'tested':summary['tested'],'finalists':summary['finalists'],
                    'holdout_positive':summary['holdout_positive'],'spartan_survivors':len(passed),
                    'distinct_survivor_behaviours':len(distinct),'completed_at':time.time()}
            save_state(public);print(json.dumps({'event':'campaign_examined',**public}),flush=True)
            # Queen receives only coarse ecological outcome, never examiner thresholds or answers.
            if passed and distinct:
                print(json.dumps({'event':'soldiers_found','count':len(passed),'distinct':len(distinct),'action':'continue breeding challengers'}),flush=True)
            else:
                print(json.dumps({'event':'extinction_pressure','action':'new independent campaign; preserve negative knowledge'}),flush=True)
        await asyncio.sleep(5)

if __name__=='__main__': asyncio.run(main())

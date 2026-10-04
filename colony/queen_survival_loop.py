"""Persistent Breeding Queen discovery loop.

Breeding Queen is the sole genome factory. She breeds on research-safe train+validation
evidence, produces ranked finalists, and hands only her top two campaign performers to
Qualification. Swarm Queen is a separate research director and never spawns genomes.
Exact Spartan thresholds/results are not fed back into breeding.
"""
import asyncio,json,os,time
from db import init_db,connection
from colony.queen_pattern_recognition import run as queen_run
from colony.spartan_v2_runner import audit_family
from colony.queen_memory import learn_campaign,record_exam_result,load_memory
from colony.queen_ecology import learn as ecology_learn,strategy as ecology_strategy
from colony.queen_experience import learn as learn_ant_experience
from colony.spartan_hall_of_fame import archive_exam
from colony.queen_roles import BREEDING_QUEEN, ROLE_VERSION

STATE='/data/queen_survival_state.json'

def save_state(x):
    os.makedirs(os.path.dirname(STATE),exist_ok=True)
    with open(STATE,'w') as f: json.dump(x,f,indent=2)

async def main():
    await init_db(); campaign=int(load_memory().get('campaigns',0) or 0)
    while True:
        campaign+=1
        async with connection() as c:
            experience=await learn_ant_experience(c)
            print(json.dumps({'event':'ant_experience_ingested','observations':experience.get('observations',0),'careers':experience.get('career_count',0),'eligible_careers':experience.get('eligible_careers',0),'reference_observations':experience.get('reference_observations',0),'reference_eligible_careers':experience.get('reference_eligible_careers',0),'preferred_features':experience.get('preferred_features',[]),'parent_templates':len(experience.get('parent_templates',[])),'quarantined_mints':len(experience.get('experienced_mints',[]))}),flush=True)
            print(json.dumps({'event':'campaign_start','campaign':campaign,'queen_role':BREEDING_QUEEN['authority'],'role_version':ROLE_VERSION,'qualification_handoff':BREEDING_QUEEN['qualification_handoff'],'batch_size':int(os.getenv('QUEEN_BATCH_SIZE','10000')),'waves':int(os.getenv('QUEEN_WAVES_PER_CAMPAIGN','2')),'directive':'PRECISION BREEDING; QUALITY OVER VOLUME'}),flush=True)
            summary,finalists=await queen_run(c,seed=300933+campaign,checkpoint='/data/queen_pattern_checkpoint.pkl')
            memory=learn_campaign(finalists,summary)
            summary['underexplored_sensors']=memory.get('underexplored_features',[])
            ecology=ecology_learn(finalists,summary,campaign); plan=ecology_strategy(ecology)
            print(json.dumps({'event':'queen_learned','memory_campaigns':memory.get('campaigns'),'preferred_features':memory.get('preferred_features',[]),'strategy':plan}),flush=True)
            audit=await audit_family(c,'queen_pattern')
            hall=await archive_exam(c,'queen_pattern',campaign,audit)
            print(json.dumps({'event':'spartan_hall_of_fame',**hall}),flush=True)
            passed=[x for x in audit['results'] if x.get('qualification_pass')]
            distinct={x.get('behaviour_id') or str(tuple(x['events'])) for x in passed}
            evaluable=[x for x in audit['results'] if x.get('evidence_sufficient') and x.get('behavioural_representative')]
            public={'campaign':campaign,'tested':summary['tested'],'finalists':summary['finalists'],
                    'holdout_positive':summary['holdout_positive'],'spartan_survivors':len(passed),
                    'distinct_survivor_behaviours':len(distinct),'spartan_evaluable_behaviours':len(evaluable),
                    'exam_inconclusive':len(evaluable)==0,'completed_at':time.time(),
                    'queen_role':BREEDING_QUEEN['authority'],'role_version':ROLE_VERSION,
                    'qualification_handoff':BREEDING_QUEEN['qualification_handoff']}
            save_state(public);record_exam_result(public);print(json.dumps({'event':'campaign_examined',**public}),flush=True)
            # Queen receives only coarse ecological outcome, never examiner thresholds or answers.
            if public['exam_inconclusive']:
                print(json.dumps({'event':'spartan_exam_inconclusive','evaluable_behaviours':0,'action':'do not count as drought; gather independent sensor-complete evidence'}),flush=True)
            elif passed and distinct:
                print(json.dumps({'event':'soldiers_found','count':len(passed),'distinct':len(distinct),'action':'continue breeding challengers'}),flush=True)
            else:
                print(json.dumps({'event':'extinction_pressure','evaluable_behaviours':len(evaluable),'action':'new independent campaign; preserve negative knowledge'}),flush=True)
        # At campaign boundaries the separate Swarm research director may review research-safe
        # ecology and suggest bounded search allocation. It never creates or mutates genomes;
        # only Breeding Queen can turn those priorities into descendants.
        persistent_campaign=int(memory.get('campaigns',campaign) or campaign)
        if persistent_campaign % int(os.getenv('SWARM_STRATEGIC_EVERY_CAMPAIGNS','1')) == 0:
            try:
                async with connection() as sc:
                    await sc.execute("CREATE TABLE IF NOT EXISTS swarm_strategy_requests(id BIGSERIAL PRIMARY KEY,campaign INTEGER NOT NULL UNIQUE,requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),started_at TIMESTAMPTZ,completed_at TIMESTAMPTZ,status TEXT NOT NULL DEFAULT 'pending',result JSONB)")
                    await sc.execute("INSERT INTO swarm_strategy_requests(campaign) VALUES($1) ON CONFLICT(campaign) DO NOTHING",persistent_campaign)
                # Advisory review is queued only. Breeding/cooldown never waits for model latency.
                print(json.dumps({'event':'swarm_strategic_review_queued','campaign':persistent_campaign}),flush=True)
            except Exception as ex:
                print(json.dumps({'event':'swarm_strategic_review_error','campaign':persistent_campaign,'error':repr(ex)[:180]}),flush=True)
        cooldown=max(300,int(os.getenv('QUEEN_CAMPAIGN_COOLDOWN_SECONDS','86400')))
        print(json.dumps({'event':'breeding_cooldown','seconds':cooldown,'policy':'quality_over_volume'}),flush=True)
        await asyncio.sleep(cooldown)

if __name__=='__main__': asyncio.run(main())

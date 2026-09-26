"""Read-only human conversation context for the Queen/Core."""
from db import connection
from colony.niche_pipeline import candidates as niche_candidates
from colony.independence import opportunity_report

async def context(run_id):
    async with connection() as conn:
        run=await conn.fetchrow("SELECT generation,status,population FROM colony_forward_runs WHERE run_id=$1",run_id)
        latest=await conn.fetchrow("SELECT max(candidate_id) cutoff,count(*) entries FROM colony_forward_entries WHERE run_id=$1",run_id)
        plans=await conn.fetchval("SELECT count(*) FROM colony_shadow_plans WHERE run_id=$1",run_id)
    return {'identity':'Queen/Core','authority':'advisory_only','run_id':run_id,
      'generation':run['generation'] if run else None,'frozen':(run['status']=='frozen') if run else None,
      'evidence_cutoff':latest['cutoff'] if latest else None,'entries':latest['entries'] if latest else 0,
      'shadow_plans':plans,'independent_opportunities':await opportunity_report(run_id),
      'niche_candidates':await niche_candidates(run_id)}

async def answerable_topics():
    return ['colony status','why an experiment was proposed','current hypotheses','evidence gaps',
            'what the colony has learned','what data it wants next','why Sceptic vetoed something']

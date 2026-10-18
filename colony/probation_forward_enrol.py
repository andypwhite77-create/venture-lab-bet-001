"""Enroll newly admitted Spartan finalists into strictly forward, observation-only paper research.
No Canary approval, signer, or real-money authorization.
"""
import json
from colony.live_registry import ensure_schema as registry_schema
from colony.finalist_probation import ensure_schema as probation_schema
async def run(conn):
 await registry_schema(conn);await probation_schema(conn)
 await conn.execute('''CREATE TABLE IF NOT EXISTS controlled_paper_cohort(genome_id text PRIMARY KEY,family text NOT NULL,started_at timestamptz NOT NULL,status text NOT NULL,purpose text NOT NULL)''')
 rows=await conn.fetch("SELECT genome_id,campaign,genome,family,admitted_at FROM finalist_probation WHERE status='awaiting_prospective_engine' ORDER BY admitted_at LIMIT 12")
 count=0
 for row in rows:
  g=row['genome'];g=json.loads(g) if isinstance(g,str) else dict(g or {})
  if not g or not g.get('parameters'):continue
  async with conn.transaction():
   # A fresh clock is taken at registration; historical candidates can never qualify.
   existing=await conn.fetchval('SELECT 1 FROM live_ant_registry WHERE genome_id=$1',row['genome_id'])
   if existing:continue
   await conn.execute('''INSERT INTO live_ant_registry(genome_id,family,species,lineage,source,genome,live_candidate,promotion_stage,spartan_passed,live_authorized,notes)
     VALUES($1,$2,$3,$2,'probation_forward',$4::jsonb,true,'reference-testing',true,false,jsonb_build_object('prospective_after',extract(epoch FROM clock_timestamp()),'probation_campaign',$5))''',
     row['genome_id'],row['family'],g.get('species'),json.dumps(g),row['campaign'])
   await conn.execute('''INSERT INTO controlled_paper_cohort(genome_id,family,started_at,status,purpose)
     VALUES($1,$2,clock_timestamp(),'observation_only','new_spartan_finalist_probation') ON CONFLICT DO NOTHING''',row['genome_id'],row['family'])
   await conn.execute("UPDATE finalist_probation SET status='prospective_observation' WHERE genome_id=$1 AND campaign=$2",row['genome_id'],row['campaign'])
   count+=1
 return {'enrolled':count,'authority':'observation_only_no_live'}

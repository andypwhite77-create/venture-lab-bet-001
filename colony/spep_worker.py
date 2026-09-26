"""Append-only SPEP recorder. Every frozen genome evaluates every exogenous candidate event."""
import json,hashlib
from db import connection
from colony.spep import VERSION,event_id,decision,twins
from colony.genome import genome_id

async def process(run_id='fwd-g3-20260926T084022Z',limit=250):
 async with connection() as c:
  schema=__import__('pathlib').Path(__file__).with_name('spep_schema.sql').read_text(); await c.execute(schema)
  run=await c.fetchrow('SELECT population FROM colony_forward_runs WHERE run_id=$1',run_id)
  if not run:return {'events':0,'decisions':0,'reason':'run_missing'}
  pop=run['population']; pop=json.loads(pop) if isinstance(pop,str) else pop
  rows=await c.fetch('''SELECT id,created_at,mint,features,market FROM research_candidates
    WHERE id > COALESCE((SELECT max(candidate_id) FROM colony_spep_events WHERE generator_version=$1),0)
    ORDER BY id LIMIT $2''',VERSION,limit)
  ne=nd=0
  for r0 in rows:
   r=dict(r0); eid=event_id(r); obs=json.dumps(r,default=str,sort_keys=True,separators=(',',':')); oh=hashlib.sha256(obs.encode()).hexdigest()
   got=await c.execute('''INSERT INTO colony_spep_events(event_id,generator_version,candidate_id,observed_at,mint,observation,observation_hash)
     VALUES($1,$2,$3,$4,$5,$6::jsonb,$7) ON CONFLICT DO NOTHING''',eid,VERSION,r['id'],r['created_at'],r['mint'],obs,oh); ne+=int(got.endswith('1'))
   for g in pop:
    gid=genome_id(g); a=decision(g,r); t=twins(a,eid,gid)
    got=await c.execute('''INSERT INTO colony_spep_decisions(event_id,genome_id,population,family,original_action,mirror_action,random_action)
      VALUES($1,$2,'gen3-parent',$3,$4,$5,$6) ON CONFLICT DO NOTHING''',eid,gid,g['family'],t['original'],t['mirror'],t['random_direction']);nd+=int(got.endswith('1'))
  return {'events':ne,'decisions':nd,'events_seen':len(rows),'genomes':len(pop),'generator':VERSION}

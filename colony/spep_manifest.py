"""Freeze a SPEP T0 manifest before prospective collection begins."""
import hashlib,json,subprocess,os
from datetime import datetime,timezone
from db import connection
from colony.spep import panel_manifest,VERSION
async def freeze(run_id):
 async with connection() as c:
  schema=__import__('pathlib').Path(__file__).with_name('spep_schema.sql').read_text();await c.execute(schema)
  old=await c.fetchrow('SELECT * FROM colony_spep_manifests WHERE run_id=$1 ORDER BY created_at DESC LIMIT 1',run_id)
  if old:return dict(old)
  run=await c.fetchrow('SELECT population FROM colony_forward_runs WHERE run_id=$1',run_id);pop=run['population'];pop=json.loads(pop) if isinstance(pop,str) else pop
  base=panel_manifest(pop);base.update({'run_id':run_id,'t0':datetime.now(timezone.utc).isoformat(),'git_commit':os.getenv('SPEP_CODE_VERSION','image-content-v1')})
  body=json.dumps(base,sort_keys=True,separators=(',',':'));h=hashlib.sha256(body.encode()).hexdigest();mid='spep_manifest_'+h[:16]
  await c.execute('INSERT INTO colony_spep_manifests(manifest_id,t0,run_id,git_commit,event_generator,counterfactual_version,population_hash,manifest,manifest_hash) VALUES($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9)',mid,datetime.fromisoformat(base['t0']),run_id,base['git_commit'],VERSION,base['counterfactuals'],base['population_hash'],body,h)
  return base|{'manifest_id':mid,'manifest_hash':h}

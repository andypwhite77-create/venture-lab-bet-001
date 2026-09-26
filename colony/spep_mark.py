"""Mark SPEP counterfactual policies from already-prospective research outcomes."""
from db import connection
from colony.spep_value import marginal_value
VARIANTS=('original','mirror','random','participation')
COL={'original':'original_action','mirror':'mirror_action','random':'random_action','participation':'participation_action'}
async def mark(limit=5000,friction_pct=0.0):
 async with connection() as c:
  rows=await c.fetch('''SELECT e.event_id,e.candidate_id,d.genome_id,d.population,d.original_action,d.mirror_action,d.random_action,d.participation_action,
   o.horizon_minutes,o.net_return_pct FROM colony_spep_events e JOIN colony_spep_decisions d USING(event_id)
   JOIN research_outcomes o ON o.candidate_id=e.candidate_id AND o.measured_at>=e.observed_at
   ORDER BY e.candidate_id,o.horizon_minutes LIMIT $1''',limit)
  n=0
  for r in rows:
   for v in VARIANTS:
    action=r[COL[v]]; net=marginal_value(r['net_return_pct'],action,friction_pct)
    q=await c.execute('''INSERT INTO colony_spep_marks(event_id,genome_id,population,policy_variant,horizon_minutes,gross_return_pct,friction_pct,net_return_pct,measured_at)
      VALUES($1,$2,$3,$4,$5,$6,$7,$8,now()) ON CONFLICT DO NOTHING''',r['event_id'],r['genome_id'],r['population'],v,r['horizon_minutes'],float(r['net_return_pct']) if action!='abstain' else 0.0,float(friction_pct),net)
    n+=int(q.endswith('1'))
  return {'marks':n,'source_rows':len(rows),'variants':VARIANTS}

"""Frozen prospective shadow trial. Never emits orders or changes reference DNA.
Only signals recorded after the trial's inception count; decisions are immutable.
"""
import asyncio,json
from db import init_db,connection
from colony.ant_plasticity_shadow import evaluate

SCHEMA="""
CREATE TABLE IF NOT EXISTS plasticity_forward_trial(
 id integer primary key CHECK(id=1), started_at timestamptz not null default now(),
 policy jsonb not null, authority text not null default 'paper_observation_only');
CREATE TABLE IF NOT EXISTS plasticity_forward_decisions(
 entry_id bigint primary key references eve_reference_paper_entries(id),
 genome_id text not null, observed_at timestamptz not null,
 action text not null, regime text not null, known_marks integer not null,
 recorded_at timestamptz not null default now());
"""
POLICY={'version':'plasticity_shadow_v2_frozen','window':8,'min_history':4,'cooldown_losses':3,'half_life_hours':24}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  await c.execute("INSERT INTO plasticity_forward_trial(id,policy) VALUES(1,$1::jsonb) ON CONFLICT DO NOTHING",json.dumps(POLICY))
  trial=await c.fetchrow('SELECT started_at,policy FROM plasticity_forward_trial WHERE id=1')
  policy=trial['policy'];policy=json.loads(policy) if isinstance(policy,str) else policy
  if policy!=POLICY:raise ValueError('frozen_policy_mismatch')
  entries=await c.fetch("""SELECT e.id entry_id,e.genome_id,e.observed_at,r.features
    FROM eve_reference_paper_entries e JOIN research_candidates r ON r.id=e.candidate_id
    JOIN controlled_paper_cohort cohort ON cohort.genome_id=e.genome_id
    WHERE cohort.status='observation_only' AND e.observed_at>=cohort.started_at
    AND e.observed_at>=$1 ORDER BY e.observed_at,e.id""",trial['started_at'])
  marked=await c.fetch("""SELECT l.entry_id,l.genome_id,l.outcome_at,l.net_return_pct net_pct
    FROM controlled_paper_trade_ledger l JOIN controlled_paper_cohort cohort ON cohort.genome_id=l.genome_id
    WHERE cohort.status='observation_only' AND l.outcome_at<now() ORDER BY l.outcome_at,l.entry_id""")
  by={}
  for x in marked:by.setdefault(x['genome_id'],[]).append(dict(x))
  decided=evaluate([dict(x) for x in entries],by,**{k:v for k,v in policy.items() if k!='version'})
  new=0
  for x in decided:
   # Do not turn a historical entry into a prospective decision: the entry must
   # have been created recently enough to still be observationally actionable.
   # Refuse any newly discovered entry older than 10 minutes.
   if (await c.fetchval('SELECT now()'))-x['observed_at'] > __import__('datetime').timedelta(minutes=10):continue
   tag=await c.execute("""INSERT INTO plasticity_forward_decisions(entry_id,genome_id,observed_at,action,regime,known_marks)
    VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING""",x['entry_id'],x['genome_id'],x['observed_at'],x['shadow_action'],x['regime'],x['known_marks'])
   new+=int(tag.endswith('1'))
  totals=await c.fetchrow("""SELECT count(*)::int total,count(*) FILTER (WHERE action='abstain')::int abstained,
   count(*) FILTER (WHERE action='follow_dna')::int followed FROM plasticity_forward_decisions""")
  comparison=await c.fetchrow("""SELECT count(l.entry_id)::int completed,
    count(l.entry_id) FILTER (WHERE d.action='abstain')::int marked_skipped,
    coalesce(sum(l.paper_pnl_gbp),0)::float8 fixed_dna_paper_pnl_gbp,
    coalesce(sum(l.paper_pnl_gbp) FILTER (WHERE d.action='follow_dna'),0)::float8 adaptive_paper_pnl_gbp
    FROM plasticity_forward_decisions d LEFT JOIN controlled_paper_trade_ledger l ON l.entry_id=d.entry_id""")
  return {'trial_started_at':trial['started_at'].isoformat(),'new_decisions':new,**dict(totals),**dict(comparison),
    'authority':'prospective_shadow_only_no_breeding_no_live','note':'Matched paper marks, not executable fills or capital-normalized returns.'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

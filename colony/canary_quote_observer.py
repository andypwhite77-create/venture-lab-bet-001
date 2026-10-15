"""Bounded read-only forward Jupiter observations for fixed reference paper entries.
Never signs, trades, or treats a delayed quote as contemporaneous evidence.
"""
import asyncio,json
from datetime import datetime,timezone
from db import init_db,connection
from colony.jupiter_quotes import quote,SOL
SCHEMA="""CREATE TABLE IF NOT EXISTS canary_forward_quote_observations(
 entry_id bigint not null references eve_reference_paper_entries(id),
 phase text not null check(phase in ('entry','exit')),
 observed_at timestamptz not null default now(), due_at timestamptz not null,
 quote jsonb, status text not null, reason text, latency_seconds double precision,
 primary key(entry_id,phase));"""
async def observe_fresh_entries(conn, keys):
 """Capture quotes at the reference-entry creation site, with a strict lateness veto."""
 await conn.execute(SCHEMA)
 await conn.execute('ALTER TABLE canary_forward_quote_observations ADD COLUMN IF NOT EXISTS latency_seconds double precision')
 recorded=0
 for genome_id,candidate_id in keys:
  e=await conn.fetchrow("""SELECT e.id,e.mint,e.observed_at FROM eve_reference_paper_entries e
    WHERE e.genome_id=$1 AND e.candidate_id=$2""",genome_id,candidate_id)
  if not e:continue
  now=datetime.now(timezone.utc);age=(now-e['observed_at']).total_seconds()
  if age<0 or age>120:continue
  exists=await conn.fetchval("SELECT 1 FROM canary_forward_quote_observations WHERE entry_id=$1 AND phase='entry'",e['id'])
  if exists:continue
  q=None;reason=None
  try:q=await asyncio.to_thread(quote,SOL,e['mint'],10000000,100,3)
  except Exception as exc:reason=type(exc).__name__
  latency=(datetime.now(timezone.utc)-e['observed_at']).total_seconds()
  await conn.execute("""INSERT INTO canary_forward_quote_observations
    (entry_id,phase,due_at,quote,status,reason,latency_seconds)
    VALUES($1,'entry',$2,$3::jsonb,$4,$5,$6) ON CONFLICT DO NOTHING""",
    e['id'],e['observed_at'],json.dumps(q) if q else None,
    'quoted' if q else 'unavailable',reason,latency)
  recorded+=1
 return recorded

async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  await c.execute("ALTER TABLE canary_forward_quote_observations ADD COLUMN IF NOT EXISTS latency_seconds double precision")
  records=await c.fetch("""SELECT e.id,e.mint,e.observed_at,e.hold_minutes,e.stake_gbp,
    e.observed_at+e.hold_minutes*interval '1 minute' exit_due,
    q.quote entry_quote FROM eve_reference_paper_entries e
    JOIN controlled_paper_cohort cohort ON cohort.genome_id=e.genome_id
    LEFT JOIN canary_forward_quote_observations q ON q.entry_id=e.id AND q.phase='entry' AND q.status='quoted'
    WHERE cohort.status='observation_only' AND e.observed_at>=cohort.started_at
    AND (e.observed_at>now()-interval '2 minutes' OR
       e.observed_at+e.hold_minutes*interval '1 minute' BETWEEN now()-interval '2 minutes' AND now())
    ORDER BY e.observed_at DESC LIMIT 45""")
  count=0; successes=0
  for e in records:
   now=await c.fetchval('SELECT now()')
   for phase,due in (('entry',e['observed_at']),('exit',e['exit_due'])):
    age=(now-due).total_seconds()
    if age<0 or age>120:continue
    exists=await c.fetchval('SELECT 1 FROM canary_forward_quote_observations WHERE entry_id=$1 AND phase=$2',e['id'],phase)
    if exists:continue
    status='unavailable';reason=None;q=None
    try:
     if phase=='entry':
      # Fixed small reference size, no price conversion used for execution.
      q=await asyncio.to_thread(quote,SOL,e['mint'],10000000,100,4)
     else:
      entry=e['entry_quote'];entry=json.loads(entry) if isinstance(entry,str) else entry
      if not entry or not entry.get('out_amount'):
       reason='missing_contemporaneous_entry_quote'
      else:q=await asyncio.to_thread(quote,e['mint'],SOL,int(entry['out_amount']),100,4)
     if q:status='quoted';successes+=1
    except Exception as exc:reason=type(exc).__name__
    latency=(datetime.now(timezone.utc)-due).total_seconds()
    await c.execute("""INSERT INTO canary_forward_quote_observations
      (entry_id,phase,due_at,quote,status,reason,latency_seconds) VALUES($1,$2,$3,$4::jsonb,$5,$6,$7) ON CONFLICT DO NOTHING""",
      e['id'],phase,due,json.dumps(q) if q else None,status,reason,latency)
    count+=1
  return {'processed':count,'quotes':successes,'authority':'read_only_no_live','note':'Quote evidence only; no fills and no guaranteed execution.'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

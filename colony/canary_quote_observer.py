"""Bounded read-only forward Jupiter observations for fixed reference paper entries.
Never signs, trades, or treats a delayed quote as contemporaneous evidence.
"""
import asyncio,json,time
from datetime import datetime,timezone
from db import init_db,connection
from colony.jupiter_quotes import quote,SOL
SCHEMA="""CREATE TABLE IF NOT EXISTS canary_forward_quote_observations(
 entry_id bigint not null references eve_reference_paper_entries(id),
 phase text not null check(phase in ('entry','exit')),
 observed_at timestamptz not null default now(), due_at timestamptz not null,
 quote jsonb, status text not null, reason text, latency_seconds double precision, request_started_at timestamptz, response_at timestamptz, request_duration_ms double precision, observation_source text,
 primary key(entry_id,phase));"""
async def ensure_timing_columns(conn):
 await conn.execute(SCHEMA)
 for name,typ in [('request_started_at','timestamptz'),('response_at','timestamptz'),('request_duration_ms','double precision'),('observation_source','text')]:
  await conn.execute(f'ALTER TABLE canary_forward_quote_observations ADD COLUMN IF NOT EXISTS {name} {typ}')

async def observe_fresh_entries(conn, keys):
 """Capture quotes at the reference-entry creation site, with a strict lateness veto."""
 await ensure_timing_columns(conn)
 recorded=0
 for genome_id,candidate_id in keys:
  e=await conn.fetchrow("""SELECT e.id,e.mint,e.observed_at FROM eve_reference_paper_entries e
    WHERE e.genome_id=$1 AND e.candidate_id=$2""",genome_id,candidate_id)
  if not e:continue
  now=datetime.now(timezone.utc);age=(now-e['observed_at']).total_seconds()
  if age<0 or age>120:continue
  exists=await conn.fetchval("SELECT 1 FROM canary_forward_quote_observations WHERE entry_id=$1 AND phase='entry'",e['id'])
  if exists:continue
  q=None;reason=None;started=datetime.now(timezone.utc);clock=time.monotonic()
  try:q=await asyncio.to_thread(quote,SOL,e['mint'],10000000,100,3)
  except Exception as exc:reason=str(exc)[:220] if hasattr(exc,'attempts') else type(exc).__name__
  responded=datetime.now(timezone.utc);duration=(time.monotonic()-clock)*1000
  latency=(responded-e['observed_at']).total_seconds()
  await conn.execute("""INSERT INTO canary_forward_quote_observations
    (entry_id,phase,due_at,quote,status,reason,latency_seconds,request_started_at,response_at,request_duration_ms,observation_source)
    VALUES($1,'entry',$2,$3::jsonb,$4,$5,$6,$7,$8,$9,'direct_paper_entry') ON CONFLICT DO NOTHING""",
    e['id'],e['observed_at'],json.dumps(q) if q else None,
    'quoted' if q else 'unavailable',reason,latency,started,responded,duration)
  recorded+=1
 return recorded

async def run():
 await init_db()
 async with connection() as c:
  await ensure_timing_columns(c)
  from colony.candidate_birth_quotes import SCHEMA as BIRTH_SCHEMA
  await c.execute(BIRTH_SCHEMA)
  # Reuse actual at-birth quotes for multiple paper genomes seeing the SAME candidate.
  # Preserve original quote clock and flag independent opportunity at candidate level.
  await c.execute("""INSERT INTO canary_forward_quote_observations
    (entry_id,phase,observed_at,due_at,quote,status,reason,latency_seconds,
     request_started_at,response_at,request_duration_ms,observation_source)
    SELECT e.id,'entry',b.response_at,e.observed_at,b.quote,b.status,b.reason,
           b.latency_seconds,b.request_started_at,b.response_at,b.request_duration_ms,'candidate_birth'
    FROM eve_reference_paper_entries e
    JOIN research_candidate_birth_quotes b ON b.candidate_id=e.candidate_id
    JOIN controlled_paper_cohort cohort ON cohort.genome_id=e.genome_id
    WHERE cohort.status='observation_only' AND e.observed_at>=cohort.started_at
      AND b.latency_seconds BETWEEN 0 AND 120
    ON CONFLICT DO NOTHING""")
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
    # Give candidate-birth capture time to persist before requesting the same
    # entry quote again; this avoids avoidable calls during provider 429s.
    if phase=='entry' and age<12:continue
    # Give the precise exit observer first opportunity; cron is late fallback.
    if phase=='exit' and age<12:continue
    exists=await c.fetchval('SELECT 1 FROM canary_forward_quote_observations WHERE entry_id=$1 AND phase=$2',e['id'],phase)
    if exists:continue
    status='unavailable';reason=None;q=None;started=datetime.now(timezone.utc);clock=time.monotonic()
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
    except Exception as exc:reason=str(exc)[:220] if hasattr(exc,'attempts') else type(exc).__name__
    responded=datetime.now(timezone.utc);duration=(time.monotonic()-clock)*1000
    latency=(responded-due).total_seconds()
    await c.execute("""INSERT INTO canary_forward_quote_observations
      (entry_id,phase,due_at,quote,status,reason,latency_seconds,request_started_at,response_at,request_duration_ms,observation_source) VALUES($1,$2,$3,$4::jsonb,$5,$6,$7,$8,$9,$10,'minute_fallback') ON CONFLICT DO NOTHING""",
      e['id'],phase,due,json.dumps(q) if q else None,status,reason,latency,started,responded,duration)
    count+=1
  return {'processed':count,'quotes':successes,'authority':'read_only_no_live','note':'Quote evidence only; no fills and no guaranteed execution.'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

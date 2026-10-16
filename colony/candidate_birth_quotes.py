"""Research-only, bounded, nonblocking Jupiter quote at candidate creation.
Never signs, never broadcasts. Captures failures and lateness rather than inventing fills.
"""
import asyncio,json,time,logging
from datetime import datetime,timezone
from db import connection
from colony.jupiter_quotes import quote,SOL
log=logging.getLogger(__name__)
SCHEMA='''CREATE TABLE IF NOT EXISTS research_candidate_birth_quotes(
 candidate_id bigint PRIMARY KEY REFERENCES research_candidates(id),
 request_started_at timestamptz NOT NULL,
 response_at timestamptz NOT NULL,
 latency_seconds double precision NOT NULL,
 request_duration_ms double precision NOT NULL,
 quote jsonb,status text NOT NULL,reason text,
 authority text NOT NULL DEFAULT 'read_only_research');'''
_SEM=asyncio.Semaphore(3)
_TASKS=set()
async def capture_candidate(candidate_id,mint):
 async with _SEM:
  async with connection() as c:
   await c.execute(SCHEMA)
   created=await c.fetchval('SELECT created_at FROM research_candidates WHERE id=$1',candidate_id)
   if created is None:return
   started=datetime.now(timezone.utc)
   if (started-created).total_seconds()>10:return
   timer=time.monotonic();result=None;reason=None
   try:result=await asyncio.to_thread(quote,SOL,mint,10000000,100,3)
   except Exception as ex:reason=str(ex)[:220] if hasattr(ex,'attempts') else type(ex).__name__
   ended=datetime.now(timezone.utc)
   await c.execute('''INSERT INTO research_candidate_birth_quotes
     (candidate_id,request_started_at,response_at,latency_seconds,request_duration_ms,quote,status,reason)
     VALUES($1,$2,$3,$4,$5,$6::jsonb,$7,$8) ON CONFLICT DO NOTHING''',
     candidate_id,started,ended,(ended-created).total_seconds(),
     (time.monotonic()-timer)*1000,json.dumps(result) if result else None,
     'quoted' if result else 'unavailable',reason)

def start_candidate_capture(candidate_id,mint):
 if len(_TASKS)>=24:return False
 task=asyncio.create_task(capture_candidate(candidate_id,mint))
 _TASKS.add(task)
 def finished(t):
  _TASKS.discard(t)
  try:t.result()
  except Exception:log.exception('candidate_birth_quote_failed')
 task.add_done_callback(finished)
 return True

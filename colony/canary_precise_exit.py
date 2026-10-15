"""Read-only short-interval exit quote scheduler. Never signs or broadcasts."""
import asyncio,json,time,logging
from datetime import datetime,timezone
from db import init_db,connection
from colony.jupiter_quotes import quote,SOL
from colony.canary_quote_observer import ensure_timing_columns
log=logging.getLogger(__name__)
async def poll():
 async with connection() as c:
  rows=await c.fetch('''SELECT e.id,e.mint,e.observed_at+e.hold_minutes*interval '1 minute' due,
      a.quote entry_quote FROM eve_reference_paper_entries e
      JOIN controlled_paper_cohort cohort ON cohort.genome_id=e.genome_id AND cohort.status='observation_only'
      LEFT JOIN canary_forward_quote_observations a ON a.entry_id=e.id AND a.phase='entry' AND a.status='quoted'
      LEFT JOIN canary_forward_quote_observations x ON x.entry_id=e.id AND x.phase='exit'
      WHERE x.entry_id IS NULL AND e.observed_at>=cohort.started_at
      AND e.observed_at+e.hold_minutes*interval '1 minute' BETWEEN now()-interval '5 seconds' AND now()+interval '7 seconds'
      ORDER BY due LIMIT 15''')
  # Batch candidate lookups, but only quotes with actual due times are sampled.
  for r in rows:
   delay=(r['due']-datetime.now(timezone.utc)).total_seconds()
   if delay>0:await asyncio.sleep(delay)
   started=datetime.now(timezone.utc);clock=time.monotonic();q=None;reason=None
   e=r['entry_quote'];e=json.loads(e) if isinstance(e,str) else e
   try:
    if not e or not int(e.get('out_amount') or 0):reason='missing_contemporaneous_entry_quote'
    else:q=await asyncio.to_thread(quote,r['mint'],SOL,int(e['out_amount']),100,3)
   except Exception as ex:reason=type(ex).__name__
   responded=datetime.now(timezone.utc);latency=(responded-r['due']).total_seconds()
   async with connection() as c:
    await c.execute('''INSERT INTO canary_forward_quote_observations
      (entry_id,phase,observed_at,due_at,quote,status,reason,latency_seconds,request_started_at,response_at,request_duration_ms,observation_source)
      VALUES($1,'exit',$2,$3,$4::jsonb,$5,$6,$7,$8,$9,$10,'precise_exit') ON CONFLICT DO NOTHING''',
      r['id'],responded,r['due'],json.dumps(q) if q else None,'quoted' if q else 'unavailable',reason,
      latency,started,responded,(time.monotonic()-clock)*1000)
 return len(rows)
async def main():
 await init_db()
 async with connection() as c:
  await ensure_timing_columns(c)
  await c.execute("CREATE INDEX IF NOT EXISTS eve_reference_observed_hold_idx ON eve_reference_paper_entries (observed_at,hold_minutes)")
  await c.execute("CREATE INDEX IF NOT EXISTS canary_quote_phase_entry_idx ON canary_forward_quote_observations(entry_id,phase,status)")
 while True:
  try:await poll()
  except Exception:log.exception('precise_exit_poll_failure')
  await asyncio.sleep(1)
if __name__=='__main__':
 logging.basicConfig(level=logging.INFO)
 asyncio.run(main())

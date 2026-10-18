"""Cross-process Jupiter quote admission; fail closed, no delayed observations."""
import asyncio,os
import asyncpg
DSN=os.getenv('DATABASE_URL','')
INTERVAL=max(0.1,float(os.getenv('JUPITER_SHARED_MIN_INTERVAL_SECONDS','1.2')))
LOCK=74620183
async def _acquire():
 conn=await asyncpg.connect(DSN,timeout=2)
 try:
  if not await conn.fetchval('SELECT pg_try_advisory_lock($1)',LOCK):return False
  try:
   await conn.execute('CREATE TABLE IF NOT EXISTS jupiter_shared_budget(id boolean PRIMARY KEY DEFAULT true CHECK(id),last_request timestamptz NOT NULL DEFAULT to_timestamp(0))')
   await conn.execute('INSERT INTO jupiter_shared_budget(id) VALUES(true) ON CONFLICT DO NOTHING')
   return bool(await conn.fetchval("UPDATE jupiter_shared_budget SET last_request=clock_timestamp() WHERE id=true AND last_request <= clock_timestamp() - ($1 * interval '1 second') RETURNING id",INTERVAL))
  finally:await conn.execute('SELECT pg_advisory_unlock($1)',LOCK)
 finally:await conn.close()
def acquire():
 if not DSN:return False
 try:return asyncio.run(_acquire())
 except Exception:return False

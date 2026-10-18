"""Cross-container PostgreSQL token budget, fail closed. A reservation is a request, not a price tick."""
from db import connection
SCHEMA='''CREATE TABLE IF NOT EXISTS provider_request_budget(provider text NOT NULL,bucket bigint NOT NULL,used integer NOT NULL DEFAULT 0,PRIMARY KEY(provider,bucket));'''
async def reserve(provider,limit=80):
 try:
  async with connection() as c:
   await c.execute(SCHEMA)
   return bool(await c.fetchval('''WITH b AS (INSERT INTO provider_request_budget(provider,bucket,used)
    VALUES($1,floor(extract(epoch from clock_timestamp())/60)::bigint,1)
    ON CONFLICT(provider,bucket) DO UPDATE SET used=provider_request_budget.used+1
    WHERE provider_request_budget.used<$2 RETURNING used)
    SELECT EXISTS(SELECT 1 FROM b)''',provider,limit))
 except Exception:
  return False

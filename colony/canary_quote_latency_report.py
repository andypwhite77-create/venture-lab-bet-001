"""Read-only quote latency by actual capture source; no execution claims."""
import asyncio,json
from db import init_db,connection
async def run():
 await init_db()
 async with connection() as c:
  rows=await c.fetch('''SELECT phase,coalesce(observation_source,'legacy_unknown') source,status,
     count(*)::int observations,
     round(avg(latency_seconds)::numeric,3)::float8 average_latency_seconds,
     count(*) FILTER (WHERE latency_seconds BETWEEN 0 AND 2)::int within_two_seconds,
     round(avg(request_duration_ms)::numeric,2)::float8 average_request_ms
     FROM canary_forward_quote_observations
     WHERE observed_at>now()-interval '3 hours'
     GROUP BY phase,coalesce(observation_source,'legacy_unknown'),status
     ORDER BY phase,source,status''')
 return {'window':'last_3_hours','groups':[dict(r) for r in rows],
  'qualification':'latency evidence only, not executable fills or profitability'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

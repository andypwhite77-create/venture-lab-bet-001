"""Independent pricing provenance audit; never treats fetch time as provider tick time."""
import asyncio,json
from db import init_db,connection
SCHEMA='''CREATE TABLE IF NOT EXISTS price_provenance_audits(id bigserial PRIMARY KEY,audited_at timestamptz NOT NULL DEFAULT now(),report jsonb NOT NULL);'''
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  provider_rows=await c.fetch('''SELECT provider,count(*) n,count(*) FILTER(WHERE source_observed_at IS NULL) missing_origin_time,count(*) FILTER(WHERE source_observed_at>collected_at) future_origin_time,count(*) FILTER(WHERE source_observed_at<collected_at-interval '30 seconds') stale_origin_time FROM market_price_history WHERE collected_at>=now()-interval '6 hours' GROUP BY provider ORDER BY n DESC''')
  candidates=await c.fetchrow('''SELECT count(*) total,count(*) FILTER(WHERE entry_price IS NULL) missing_entry FROM research_candidates WHERE created_at>=now()-interval '6 hours' ''')
  report={'window_hours':6,'providers':[dict(r) for r in provider_rows],'research_candidates':dict(candidates),'policy':'missing provider-origin timestamp = unknown origin freshness; never eligible as verified archived entry','price_kinds':{'geckoterminal':'reference_not_fill','dexscreener':'reference_not_fill','jupiter':'sized_route_quote_not_guaranteed_fill','kraken_ohlc':'candle_reference_not_executable'},'authority':'audit_only'}
  await c.execute('INSERT INTO price_provenance_audits(report) VALUES($1::jsonb)',json.dumps(report))
 return report
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

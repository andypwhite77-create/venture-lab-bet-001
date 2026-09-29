"""Exact live-canary shaped rehearsal with signing/broadcast physically absent.
Maintains a sequential £25 shadow wallet and 50/50 realised-profit split.
"""
import json
from db import connection
START_GBP=25.0; CAP_GBP=1000.0

async def ensure(c):
    await c.execute('''CREATE TABLE IF NOT EXISTS reversal_shadow_canary(
      id BIGSERIAL PRIMARY KEY,mint TEXT UNIQUE NOT NULL,observed_at TIMESTAMPTZ NOT NULL,
      return_pct DOUBLE PRECISION NOT NULL,before_gbp DOUBLE PRECISION NOT NULL,
      gross_after_gbp DOUBLE PRECISION NOT NULL,retained_gbp DOUBLE PRECISION NOT NULL,
      payout_gbp DOUBLE PRECISION NOT NULL,after_gbp DOUBLE PRECISION NOT NULL,
      mode TEXT NOT NULL DEFAULT 'shadow_no_signer',metadata JSONB NOT NULL DEFAULT '{}'::jsonb)''')

async def run():
    async with connection() as c:
        await ensure(c)
        state=await c.fetchrow('SELECT coalesce((SELECT after_gbp FROM reversal_shadow_canary ORDER BY id DESC LIMIT 1),$1) bal,coalesce(sum(payout_gbp),0) paid FROM reversal_shadow_canary',START_GBP)
        bal=float(state['bal']); paid=float(state['paid'])
        rows=await c.fetch('''WITH x AS (SELECT e.mint,e.observed_at,o.net_return_pct,
          row_number() over(partition by e.mint order by e.observed_at,e.id) rn
          FROM reversal_tournament_entries e JOIN reversal_tournament_ants a ON a.run_id=e.run_id AND a.genome_id=e.genome_id
          JOIN LATERAL (SELECT net_return_pct FROM research_outcomes o WHERE o.candidate_id=e.candidate_id ORDER BY abs(o.horizon_minutes-e.hold_minutes),o.horizon_minutes LIMIT 1)o ON true
          WHERE a.baseline=true AND a.active=true)
          SELECT * FROM x WHERE rn=1 AND NOT EXISTS(SELECT 1 FROM reversal_shadow_canary s WHERE s.mint=x.mint) ORDER BY observed_at''')
        added=0
        for r in rows:
            before=bal; gross=max(0.0,before*(1+float(r['net_return_pct'])/100)); profit=gross-before
            payout=max(0.0,profit*.5); retained=profit-payout; bal=min(CAP_GBP,before+retained if profit>0 else gross); paid+=payout
            await c.execute('''INSERT INTO reversal_shadow_canary(mint,observed_at,return_pct,before_gbp,gross_after_gbp,retained_gbp,payout_gbp,after_gbp,metadata)
              VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb) ON CONFLICT(mint) DO NOTHING''',r['mint'],r['observed_at'],float(r['net_return_pct']),before,gross,retained,payout,bal,json.dumps({'broadcast':False,'signer_present':False}))
            added+=1
    return {'added':added,'treasury_gbp':bal,'payout_gbp':paid,'cap_gbp':CAP_GBP,'broadcast':False,'signer_present':False}

"""Append-only evidence-graded shared Hive findings.

Promotes no ant or trading authority; requires provenance and records test class.
"""
import asyncio,json
from db import init_db,connection
GRADES={'hypothesis':0,'backtest':1,'prospective_paper':2,'independent_holdout':3,'realized_live':4}
SCHEMA="""CREATE TABLE IF NOT EXISTS hive_findings(
 id BIGSERIAL PRIMARY KEY,colony TEXT NOT NULL,claim TEXT NOT NULL,
 evidence_grade TEXT NOT NULL,source_type TEXT NOT NULL,source_id TEXT NOT NULL,
 evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(colony,source_type,source_id,claim),
 CHECK(evidence_grade IN ('hypothesis','backtest','prospective_paper','independent_holdout','realized_live')));
CREATE INDEX IF NOT EXISTS hive_findings_grade_time ON hive_findings(evidence_grade,created_at DESC);"""
def grade_value(grade):
 if grade not in GRADES:raise ValueError('invalid_evidence_grade')
 return GRADES[grade]
async def record(c,colony,claim,grade,source_type,source_id,evidence):
 grade_value(grade)
 if not colony or not claim or not source_type or not source_id:raise ValueError('missing_provenance')
 return await c.fetchval("""INSERT INTO hive_findings(colony,claim,evidence_grade,source_type,source_id,evidence)
 VALUES($1,$2,$3,$4,$5,$6::jsonb) ON CONFLICT DO NOTHING RETURNING id""",
 colony,claim,grade,source_type,source_id,json.dumps(evidence,default=str))
async def snapshot(c):
 rows=await c.fetch("""SELECT colony,claim,evidence_grade,source_type,source_id,created_at
 FROM hive_findings ORDER BY created_at DESC LIMIT 20""")
 return [dict(r) for r in rows]
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  r=await c.fetchrow("""SELECT count(*)::int n,
     coalesce(sum((execution->>'realized_market_pnl_after_network_fees_sol')::numeric),0)::float8 net
     FROM canary_trade_intents WHERE status='closed' AND broadcast
       AND execution ? 'realized_market_pnl_after_network_fees_sol'
       AND created_at>=now()-interval '7 days'""")
  import datetime
  day=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
  claim='Canary realized economic outcome: '+('negative' if r['net']<0 else 'nonnegative')
  await record(c,'solana_research',claim,'realized_live','canary_trade_intents_7d',day,
    {'trades':r['n'],'net_sol':r['net'],'rent_recovery_excluded':True,
     'note':'A seven-day rolling aggregate, not evidence of strategy causality'})
  return await snapshot(c)
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str))

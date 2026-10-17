"""Operational wallet-first roster review: evidence-gated, audit-only until attributable fills.
No automatic promotion, no selling assets and no changes to live authority.
"""
import asyncio,json
from db import init_db,connection
from colony.wallet_survival_policy import WalletEvidence,classify
SCHEMA='''CREATE TABLE IF NOT EXISTS wallet_survival_reviews(
 id bigserial primary key, reviewed_at timestamptz not null default now(),
 report jsonb not null, authority text not null default 'diagnostic_only');'''
SQL='''SELECT c.genome_id,c.canary_slot,
 count(distinct v.intent_id) observed_intents,
 count(distinct v.intent_id) FILTER(WHERE i.broadcast=true) broadcast_intents,
 count(distinct l.id) FILTER(WHERE l.broadcast=true AND l.mode<>'simulated') attributed_ledger_rows
 FROM champion_league c
 LEFT JOIN canary_intent_votes v ON v.genome_id=c.genome_id
 LEFT JOIN canary_trade_intents i ON i.id=v.intent_id
 LEFT JOIN colony_execution_ledger l ON l.intent_id=i.id::text
 WHERE c.canary_slot IS NOT NULL AND c.active=true
 GROUP BY c.genome_id,c.canary_slot ORDER BY c.canary_slot'''
def assess(rows):
 reviews=[]
 for r in rows:
  x=dict(r)
  # Votes are group signals, not per-ant wallet attribution. Ledger rows may
  # be simulated or shared; no realised per-ant profit can be inferred from them.
  x['wallet_reconciled_per_ant']=False
  x['decision']=classify(WalletEvidence(0,0,0,False,0))
  x['recommended_action']='block_new_live_allocation_pending_wallet_attribution'
  x['automatic_roster_change']=False
  reviews.append(x)
 return {'ants':reviews,'reviewed':len(reviews),'authority':'audit_only',
  'blocking_gap':'No reconciled per-ant realised wallet cashflows; shared candidate votes are not ownership of fills.',
  'decision_next':'Build wallet-fill attribution and realised cash reconciliation before automated demotion or retention.'}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  rows=await c.fetch(SQL)
  out=assess(rows)
  await c.execute('INSERT INTO wallet_survival_reviews(report) VALUES($1::jsonb)',json.dumps(out))
 return out
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

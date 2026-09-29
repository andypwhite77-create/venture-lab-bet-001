"""Matched-universe controls for Reversal: random timestamps and mechanical dip-buy.
Controls use the same research stream and a fixed 60m horizon; they never affect selection.
"""
import hashlib,json,os,random
from db import connection
START=int(os.getenv('REVERSAL_CURRENT_CODE_START_ID','0'))

def deterministic_random(candidate_id):
 return random.Random(int(hashlib.sha256(str(candidate_id).encode()).hexdigest()[:16],16)).random()<0.25

async def ensure(c):
 await c.execute('''CREATE TABLE IF NOT EXISTS reversal_paired_controls(
  id BIGSERIAL PRIMARY KEY,candidate_id BIGINT NOT NULL,mint TEXT NOT NULL,observed_at TIMESTAMPTZ NOT NULL,
  control TEXT NOT NULL,included BOOLEAN NOT NULL,return_pct DOUBLE PRECISION,metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(candidate_id,control))''')

async def collect():
 async with connection() as c:
  await ensure(c)
  rows=await c.fetch('''SELECT c.id candidate_id,c.mint,c.created_at observed_at,c.features,
    (SELECT o.net_return_pct FROM research_outcomes o WHERE o.candidate_id=c.id ORDER BY abs(o.horizon_minutes-60),o.horizon_minutes LIMIT 1) ret
    FROM research_candidates c WHERE c.id>$1 ORDER BY c.id''',START)
  touched=0
  for r in rows:
   if r['ret'] is None:continue
   f=r['features'] if isinstance(r['features'],dict) else json.loads(r['features'] or '{}')
   dip=any(float(f.get(k) or 0)<=-5.0 for k in ('price_change_m5','price_change_h1'))
   for name,inc in [('random_timestamp',deterministic_random(r['candidate_id'])),('mechanical_dip',dip)]:
    await c.execute('''INSERT INTO reversal_paired_controls(candidate_id,mint,observed_at,control,included,return_pct,metadata)
      VALUES($1,$2,$3,$4,$5,$6,$7::jsonb) ON CONFLICT(candidate_id,control) DO UPDATE SET included=EXCLUDED.included,return_pct=EXCLUDED.return_pct,metadata=EXCLUDED.metadata''',
      r['candidate_id'],r['mint'],r['observed_at'],name,inc,float(r['ret']) if inc else None,json.dumps({'horizon_minutes':60,'universe':'current_code'}));touched+=1
 return {'touched':touched}

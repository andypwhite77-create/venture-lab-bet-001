"""Immutable hypothetical cash entries derived only from validated forward quote evidence.
Each source position may reserve once and release once; no wallet transactions.
"""
from colony.quote_to_quote_ledger import valid
SCHEMA='''CREATE TABLE IF NOT EXISTS paper_cash_events (
 id bigserial PRIMARY KEY, source_entry_id bigint NOT NULL, genome_id text NOT NULL,
 action text NOT NULL CHECK(action IN ('reserve','release')),
 amount_lamports bigint NOT NULL CHECK(amount_lamports>0),
 event_at timestamptz NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(),
 evidence text NOT NULL DEFAULT 'hypothetical_quote',
 UNIQUE(source_entry_id,action));'''
async def ingest(conn):
 await conn.execute(SCHEMA)
 rows=await conn.fetch('''SELECT e.id,e.genome_id,e.observed_at,
 e.observed_at+e.hold_minutes*interval '1 minute' exit_due,
 a.quote entry_quote,a.status entry_status,a.latency_seconds entry_latency,
 x.quote exit_quote,x.status exit_status,x.latency_seconds exit_latency
 FROM eve_reference_paper_entries e
 JOIN controlled_paper_cohort cc ON cc.genome_id=e.genome_id AND cc.status='observation_only' AND e.observed_at>=cc.started_at
 LEFT JOIN canary_forward_quote_observations a ON a.entry_id=e.id AND a.phase='entry'
 LEFT JOIN canary_forward_quote_observations x ON x.entry_id=e.id AND x.phase='exit'
 ORDER BY e.genome_id,e.observed_at,e.id''')
 counts={'reserve':0,'release':0}
 for row in rows:
  r=dict(row);entry=valid(r,'entry')
  if not entry:continue
  res=await conn.execute('''INSERT INTO paper_cash_events(source_entry_id,genome_id,action,amount_lamports,event_at)
    VALUES($1,$2,'reserve',$3,$4) ON CONFLICT DO NOTHING''',r['id'],r['genome_id'],entry[0],r['observed_at'])
  counts['reserve']+=int(res.endswith('1'))
  exit_=valid(r,'exit')
  if exit_ and exit_[0]==entry[1]:
   res=await conn.execute('''INSERT INTO paper_cash_events(source_entry_id,genome_id,action,amount_lamports,event_at)
    VALUES($1,$2,'release',$3,$4) ON CONFLICT DO NOTHING''',r['id'],r['genome_id'],exit_[1],r['exit_due'])
   counts['release']+=int(res.endswith('1'))
 return counts

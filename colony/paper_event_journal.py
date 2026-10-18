"""Append-only, research-only evidence journal; no orders or signing.
Events are immutable by unique source identity. This does not infer a fill.
"""
import json
SCHEMA='''CREATE TABLE IF NOT EXISTS paper_quote_events(
 id bigserial primary key, source_entry_id bigint not null,
 phase text not null check(phase in ('entry_quote','exit_quote')),
 genome_id text not null, observed_at timestamptz not null,
 evidence jsonb not null, recorded_at timestamptz not null default now(),
 unique(source_entry_id,phase));'''
async def ingest(conn):
 await conn.execute(SCHEMA)
 return await conn.execute('''INSERT INTO paper_quote_events(source_entry_id,phase,genome_id,observed_at,evidence)
 SELECT q.entry_id,q.phase||'_quote',e.genome_id,q.observed_at,
 jsonb_build_object('status',q.status,'reason',q.reason,'quote',q.quote,'latency_seconds',q.latency_seconds,'request_started_at',q.request_started_at,'response_at',q.response_at,'due_at',q.due_at)
 FROM canary_forward_quote_observations q
 JOIN eve_reference_paper_entries e ON e.id=q.entry_id
 WHERE q.phase IN ('entry','exit')
 ON CONFLICT(source_entry_id,phase) DO NOTHING''')

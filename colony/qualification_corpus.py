"""Immutable cumulative qualification corpus.

Each observed candidate/horizon outcome is copied once from the research stream into
an append-only benchmark table. Existing rows are never updated, so later ants can
be replayed against the same accumulated market history without rewriting the exam.
"""
from __future__ import annotations
import json
from colony.replay import flatten
from colony.queen_council import archetype_signals, enrich_historical_context

VERSION='qualification-corpus-v1'

async def ensure_schema(c):
    await c.execute("""CREATE TABLE IF NOT EXISTS qualification_corpus(
      candidate_id BIGINT NOT NULL,
      horizon_minutes INT NOT NULL,
      observed_at TIMESTAMPTZ NOT NULL,
      mint TEXT NOT NULL,
      features JSONB NOT NULL DEFAULT '{}'::jsonb,
      market JSONB NOT NULL DEFAULT '{}'::jsonb,
      net_return_pct DOUBLE PRECISION NOT NULL,
      corpus_version TEXT NOT NULL DEFAULT 'qualification-corpus-v1',
      captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY(candidate_id,horizon_minutes));
    CREATE INDEX IF NOT EXISTS qualification_corpus_time ON qualification_corpus(observed_at,candidate_id);
    CREATE INDEX IF NOT EXISTS qualification_corpus_mint ON qualification_corpus(mint);""")

async def sync(c):
    await ensure_schema(c)
    before=int(await c.fetchval('SELECT count(*) FROM qualification_corpus') or 0)
    await c.execute("""INSERT INTO qualification_corpus(
      candidate_id,horizon_minutes,observed_at,mint,features,market,net_return_pct,corpus_version)
      SELECT c.id,o.horizon_minutes,c.created_at,c.mint,c.features,c.market,o.net_return_pct,$1
      FROM research_candidates c JOIN research_outcomes o ON o.candidate_id=c.id
      WHERE o.net_return_pct IS NOT NULL
      ON CONFLICT(candidate_id,horizon_minutes) DO NOTHING""",VERSION)
    after=int(await c.fetchval('SELECT count(*) FROM qualification_corpus') or 0)
    return {'inserted':after-before,'outcomes':after}

async def load_rows(c):
    await ensure_schema(c)
    rows=await c.fetch("""SELECT candidate_id,horizon_minutes,observed_at,mint,features,market,net_return_pct
      FROM qualification_corpus ORDER BY observed_at,candidate_id,horizon_minutes""")
    grouped={}
    for x in rows:
        d=grouped.setdefault(x['candidate_id'],{
            'id':x['candidate_id'],'created_at':x['observed_at'],'mint':x['mint'],
            'features':(json.loads(x['features']) if isinstance(x['features'],str) else dict(x['features'] or {})),
            'market':(json.loads(x['market']) if isinstance(x['market'],str) else dict(x['market'] or {})),
            'returns':{}})
        d['returns'][int(x['horizon_minutes'])]=float(x['net_return_pct'])
    for d in grouped.values():
        d['flat']=flatten(d)
        d['flat'].update(archetype_signals(d['flat']))
    out=list(grouped.values())
    await enrich_historical_context(c,out)
    return out

async def snapshot(c):
    await ensure_schema(c)
    r=await c.fetchrow("""SELECT count(*)::int outcomes,count(DISTINCT candidate_id)::int candidates,
      count(DISTINCT mint)::int unique_mints,count(DISTINCT observed_at::date)::int days,
      min(observed_at) first_observed,max(observed_at) last_observed
      FROM qualification_corpus""")
    horizons=[int(x['horizon_minutes']) for x in await c.fetch("SELECT DISTINCT horizon_minutes FROM qualification_corpus ORDER BY horizon_minutes")]
    return {**dict(r),'horizons':horizons,'version':VERSION}

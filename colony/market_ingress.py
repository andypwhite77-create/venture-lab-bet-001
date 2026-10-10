"""Append-only, non-authoritative market-observation history.

All records are research-only; no holdout outcomes, signing keys or credentials.
Errors are data, too. Caller owns collection cadence.
"""
import json
from db import connection

SCHEMA="""CREATE TABLE IF NOT EXISTS colony_market_ingress (
 id BIGSERIAL PRIMARY KEY,
 observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 colony TEXT NOT NULL DEFAULT 'solana_research',
 provider TEXT NOT NULL,
 mint TEXT NOT NULL,
 observation_kind TEXT NOT NULL,
 requested_size_lamports BIGINT,
 success BOOLEAN,
 response JSONB NOT NULL,
 source_ts TIMESTAMPTZ,
 provenance TEXT NOT NULL DEFAULT 'live_observation',
 CHECK (provenance='live_observation')
);
CREATE INDEX IF NOT EXISTS colony_market_ingress_mint_time
 ON colony_market_ingress(mint, observed_at DESC);
CREATE INDEX IF NOT EXISTS colony_market_ingress_provider_time
 ON colony_market_ingress(provider, observed_at DESC);
CREATE TABLE IF NOT EXISTS colony_mesh_registry (
 colony_id TEXT PRIMARY KEY,
 ecosystem TEXT NOT NULL,
 stage TEXT NOT NULL DEFAULT 'research_proposed',
 research_scope JSONB NOT NULL DEFAULT '{}',
 allocation_authorized BOOLEAN NOT NULL DEFAULT false,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(stage IN ('research_proposed','paper_research','qualified')),
 CHECK(allocation_authorized=false)
);
"""
async def capture(mint,provider,kind,response,lamports=None,colony='solana_research'):
    record=json.dumps(response,default=str)
    # Avoid pathological provider error strings or huge unsolicited responses.
    if len(record)>131072:record=json.dumps({'truncated':True,'original_bytes':len(record)})
    async with connection() as c:
        await c.execute(SCHEMA)
        return await c.fetchval("""INSERT INTO colony_market_ingress
          (mint,provider,observation_kind,requested_size_lamports,success,response,colony)
          VALUES($1,$2,$3,$4,$5,$6::jsonb,$7) RETURNING id""",
          mint,provider,kind,lamports,response.get('ok') if isinstance(response,dict) else None,
          record,colony)

async def seed_mesh():
    async with connection() as c:
        await c.execute(SCHEMA)
        for ident,ecosystem,stage in [('solana_research','solana','paper_research'),('ethereum_scout','ethereum','research_proposed'),('cross_venue_scout','multi_exchange','research_proposed')]:
            await c.execute("""INSERT INTO colony_mesh_registry(colony_id,ecosystem,stage)
             VALUES($1,$2,$3) ON CONFLICT(colony_id) DO NOTHING""",ident,ecosystem,stage)

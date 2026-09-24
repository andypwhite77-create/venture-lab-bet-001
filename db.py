import json
import os
from contextlib import asynccontextmanager

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "")
_pool = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS rpc_samples (
    id BIGSERIAL PRIMARY KEY,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    slot BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS wallets (
    address TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'unknown',
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tx_count INTEGER NOT NULL DEFAULT 0,
    swap_like_count INTEGER NOT NULL DEFAULT 0,
    score DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS observed_transactions (
    signature TEXT PRIMARY KEY,
    slot BIGINT,
    block_time TIMESTAMPTZ,
    wallet TEXT,
    source_program TEXT,
    fee_lamports BIGINT,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    native_delta_lamports BIGINT,
    token_deltas JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_observed_transactions_wallet_time
    ON observed_transactions(wallet, block_time DESC);
CREATE INDEX IF NOT EXISTS idx_observed_transactions_time
    ON observed_transactions(block_time DESC);

CREATE TABLE IF NOT EXISTS signal_events (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    signal_name TEXT NOT NULL,
    wallet TEXT,
    mint TEXT,
    direction TEXT,
    confidence DOUBLE PRECISION,
    reference_price DOUBLE PRECISION,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_signal_events_name_mint_time
    ON signal_events(signal_name, mint, created_at DESC);

CREATE TABLE IF NOT EXISTS paper_trades (
    id BIGSERIAL PRIMARY KEY,
    signal_event_id BIGINT REFERENCES signal_events(id),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    mint TEXT NOT NULL,
    side TEXT NOT NULL,
    notional_gbp DOUBLE PRECISION NOT NULL,
    entry_price DOUBLE PRECISION,
    exit_price DOUBLE PRECISION,
    estimated_cost_bps DOUBLE PRECISION NOT NULL DEFAULT 0,
    pnl_gbp DOUBLE PRECISION,
    pnl_pct DOUBLE PRECISION,
    status TEXT NOT NULL DEFAULT 'open',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS engine_events (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);
"""


async def init_db():
    global _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=4, command_timeout=30)
    async with _pool.acquire() as conn:
        await conn.execute(SCHEMA)
    return _pool


def pool():
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool


@asynccontextmanager
async def connection():
    p = pool()
    async with p.acquire() as conn:
        yield conn


async def record_rpc_sample(slot: int):
    async with connection() as conn:
        await conn.execute("INSERT INTO rpc_samples(slot) VALUES($1)", slot)


async def record_event(level: str, event_type: str, message: str, payload=None):
    async with connection() as conn:
        await conn.execute(
            "INSERT INTO engine_events(level,event_type,message,payload) VALUES($1,$2,$3,$4::jsonb)",
            level, event_type, message, json.dumps(payload or {})
        )


async def upsert_wallet(address: str, source: str):
    async with connection() as conn:
        await conn.execute(
            """
            INSERT INTO wallets(address, source, tx_count) VALUES($1,$2,1)
            ON CONFLICT(address) DO UPDATE SET
              last_seen=NOW(),
              tx_count=wallets.tx_count+1,
              source=CASE WHEN wallets.source='unknown' THEN EXCLUDED.source ELSE wallets.source END
            """,
            address, source,
        )


async def increment_swap_like(address: str):
    async with connection() as conn:
        await conn.execute(
            "UPDATE wallets SET swap_like_count=swap_like_count+1,last_seen=NOW() WHERE address=$1",
            address,
        )


async def tx_exists(signature: str) -> bool:
    async with connection() as conn:
        return bool(await conn.fetchval("SELECT 1 FROM observed_transactions WHERE signature=$1", signature))


async def save_transaction(summary: dict):
    async with connection() as conn:
        await conn.execute(
            """
            INSERT INTO observed_transactions(
              signature,slot,block_time,wallet,source_program,fee_lamports,success,
              native_delta_lamports,token_deltas,raw_summary
            ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10::jsonb)
            ON CONFLICT(signature) DO NOTHING
            """,
            summary["signature"], summary.get("slot"), summary.get("block_time"),
            summary.get("wallet"), summary.get("source_program"), summary.get("fee_lamports"),
            summary.get("success", True), summary.get("native_delta_lamports"),
            json.dumps(summary.get("token_deltas", [])), json.dumps(summary.get("raw_summary", {})),
        )


async def recent_received_tokens(window_minutes: int = 30):
    async with connection() as conn:
        rows = await conn.fetch(
            """
            SELECT t.signature, t.wallet, t.block_time,
                   d.elem->>'mint' AS mint,
                   (d.elem->>'delta')::double precision AS delta
            FROM observed_transactions t
            CROSS JOIN LATERAL jsonb_array_elements(t.token_deltas) AS d(elem)
            WHERE t.success = TRUE
              AND t.wallet IS NOT NULL
              AND t.block_time >= NOW() - ($1 * INTERVAL '1 minute')
              AND (d.elem->>'delta')::double precision > 0
            ORDER BY t.block_time DESC
            """,
            window_minutes,
        )
        return [dict(r) for r in rows]


async def signal_exists_recently(signal_name: str, mint: str, window_minutes: int) -> bool:
    async with connection() as conn:
        return bool(await conn.fetchval(
            """
            SELECT 1 FROM signal_events
            WHERE signal_name=$1 AND mint=$2
              AND created_at >= NOW() - ($3 * INTERVAL '1 minute')
            LIMIT 1
            """,
            signal_name, mint, window_minutes,
        ))


async def create_signal_event(signal_name: str, mint: str, direction: str, confidence: float, payload=None, wallet=None, reference_price=None):
    async with connection() as conn:
        return await conn.fetchval(
            """
            INSERT INTO signal_events(signal_name,wallet,mint,direction,confidence,reference_price,payload)
            VALUES($1,$2,$3,$4,$5,$6,$7::jsonb)
            RETURNING id
            """,
            signal_name, wallet, mint, direction, confidence, reference_price, json.dumps(payload or {}),
        )


async def recent_signals(limit: int = 50):
    async with connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id,created_at,signal_name,wallet,mint,direction,confidence,reference_price,payload
            FROM signal_events ORDER BY created_at DESC LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in rows]


async def counts():
    async with connection() as conn:
        row = await conn.fetchrow("""
          SELECT
            (SELECT COUNT(*) FROM wallets) AS wallets,
            (SELECT COUNT(*) FROM observed_transactions) AS transactions,
            (SELECT COUNT(*) FROM signal_events) AS signals,
            (SELECT COUNT(*) FROM paper_trades) AS paper_trades,
            (SELECT COUNT(*) FROM rpc_samples) AS rpc_samples
        """)
        return dict(row)


async def recent_wallets(limit: int = 20):
    async with connection() as conn:
        rows = await conn.fetch(
            "SELECT address,source,first_seen,last_seen,tx_count,swap_like_count,score FROM wallets ORDER BY last_seen DESC LIMIT $1",
            limit,
        )
        return [dict(r) for r in rows]

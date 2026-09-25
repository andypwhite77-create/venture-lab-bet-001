import json

from db import connection

RESEARCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_candidates (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    strategy TEXT NOT NULL,
    mint TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT 'long',
    score DOUBLE PRECISION NOT NULL,
    tier TEXT NOT NULL DEFAULT 'observe',
    shadow_trade BOOLEAN NOT NULL DEFAULT FALSE,
    entry_price DOUBLE PRECISION,
    assumed_cost_bps DOUBLE PRECISION NOT NULL DEFAULT 80,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    market JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_research_candidates_strategy_time
    ON research_candidates(strategy, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_candidates_mint_time
    ON research_candidates(mint, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_candidates_shadow_time
    ON research_candidates(shadow_trade, created_at DESC);

CREATE TABLE IF NOT EXISTS research_outcomes (
    id BIGSERIAL PRIMARY KEY,
    candidate_id BIGINT NOT NULL REFERENCES research_candidates(id) ON DELETE CASCADE,
    horizon_minutes INTEGER NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    raw_return_pct DOUBLE PRECISION,
    assumed_cost_bps DOUBLE PRECISION NOT NULL,
    net_return_pct DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(candidate_id, horizon_minutes)
);
CREATE INDEX IF NOT EXISTS idx_research_outcomes_horizon
    ON research_outcomes(horizon_minutes, created_at DESC);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id BIGSERIAL PRIMARY KEY,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mint TEXT NOT NULL,
    strategy TEXT,
    price_usd DOUBLE PRECISION,
    liquidity_usd DOUBLE PRECISION,
    volume_m5 DOUBLE PRECISION,
    volume_h1 DOUBLE PRECISION,
    price_change_m5 DOUBLE PRECISION,
    price_change_h1 DOUBLE PRECISION,
    buys_m5 INTEGER,
    sells_m5 INTEGER,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_market_snapshots_mint_time
    ON market_snapshots(mint, observed_at DESC);
"""


async def ensure_research_schema():
    async with connection() as conn:
        await conn.execute(RESEARCH_SCHEMA)


async def recent_token_events(window_minutes: int = 60):
    async with connection() as conn:
        rows = await conn.fetch(
            """
            SELECT t.signature,t.wallet,t.block_time,
                   d.elem->>'mint' AS mint,
                   (d.elem->>'delta')::double precision AS delta
            FROM observed_transactions t
            CROSS JOIN LATERAL jsonb_array_elements(t.token_deltas) AS d(elem)
            WHERE t.success=TRUE
              AND t.wallet IS NOT NULL
              AND t.block_time >= NOW() - ($1 * INTERVAL '1 minute')
              AND d.elem ? 'mint' AND d.elem ? 'delta'
            ORDER BY t.block_time DESC
            """,
            window_minutes,
        )
    return [dict(r) for r in rows]


async def candidate_exists_recently(strategy: str, mint: str, cooldown_minutes: int, tier: str | None = None) -> bool:
    async with connection() as conn:
        return bool(await conn.fetchval(
            """
            SELECT 1 FROM research_candidates
            WHERE strategy=$1 AND mint=$2
              AND ($4::text IS NULL OR tier=$4)
              AND created_at >= NOW() - ($3 * INTERVAL '1 minute')
            LIMIT 1
            """,
            strategy, mint, cooldown_minutes, tier,
        ))


async def create_candidate(strategy: str, mint: str, direction: str, score: float,
                           tier: str, shadow_trade: bool, entry_price, features: dict,
                           market: dict, assumed_cost_bps: float = 80.0):
    async with connection() as conn:
        return await conn.fetchval(
            """
            INSERT INTO research_candidates(
              strategy,mint,direction,score,tier,shadow_trade,entry_price,
              assumed_cost_bps,features,market
            ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10::jsonb)
            RETURNING id
            """,
            strategy, mint, direction, float(score), tier, bool(shadow_trade), entry_price,
            float(assumed_cost_bps), json.dumps(features or {}), json.dumps(market or {}),
        )


async def save_market_snapshot(mint: str, strategy: str, market: dict):
    async with connection() as conn:
        await conn.execute(
            """
            INSERT INTO market_snapshots(
              mint,strategy,price_usd,liquidity_usd,volume_m5,volume_h1,
              price_change_m5,price_change_h1,buys_m5,sells_m5,payload
            ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb)
            """,
            mint, strategy, market.get("price_usd"), market.get("liquidity_usd"),
            market.get("volume_m5"), market.get("volume_h1"),
            market.get("price_change_m5"), market.get("price_change_h1"),
            market.get("buys_m5"), market.get("sells_m5"), json.dumps(market or {}),
        )


async def recent_candidates(limit: int = 100, shadow_only: bool = False):
    async with connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id,created_at,strategy,mint,direction,score,tier,shadow_trade,
                   entry_price,assumed_cost_bps,features,market
            FROM research_candidates
            WHERE ($2::boolean=FALSE OR shadow_trade=TRUE)
            ORDER BY created_at DESC LIMIT $1
            """,
            limit, shadow_only,
        )
    return [dict(r) for r in rows]


async def due_candidate_outcomes(horizons_minutes, limit: int = 200):
    async with connection() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id AS candidate_id,c.created_at,c.strategy,c.mint,c.direction,
                   c.entry_price,c.assumed_cost_bps,h.horizon_minutes
            FROM research_candidates c
            CROSS JOIN UNNEST($1::int[]) AS h(horizon_minutes)
            LEFT JOIN research_outcomes o
              ON o.candidate_id=c.id AND o.horizon_minutes=h.horizon_minutes
            WHERE c.entry_price IS NOT NULL
              AND o.id IS NULL
              AND NOW() >= c.created_at + (h.horizon_minutes * INTERVAL '1 minute')
            ORDER BY c.created_at ASC,h.horizon_minutes ASC
            LIMIT $2
            """,
            list(horizons_minutes), limit,
        )
    return [dict(r) for r in rows]


async def record_candidate_outcome(candidate_id: int, horizon_minutes: int, measured_at,
                                   price: float, raw_return_pct, assumed_cost_bps: float,
                                   net_return_pct):
    async with connection() as conn:
        await conn.execute(
            """
            INSERT INTO research_outcomes(
              candidate_id,horizon_minutes,measured_at,price,raw_return_pct,
              assumed_cost_bps,net_return_pct
            ) VALUES($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT(candidate_id,horizon_minutes) DO NOTHING
            """,
            candidate_id, horizon_minutes, measured_at, price, raw_return_pct,
            assumed_cost_bps, net_return_pct,
        )


async def research_counts():
    async with connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM research_candidates) AS candidates,
              (SELECT COUNT(*) FROM research_candidates WHERE shadow_trade=TRUE) AS shadow_trades,
              (SELECT COUNT(*) FROM research_outcomes) AS outcomes,
              (SELECT COUNT(*) FROM market_snapshots) AS market_snapshots
            """
        )
    return dict(row)


async def research_scoreboard():
    async with connection() as conn:
        rows = await conn.fetch(
            """
            SELECT c.strategy,c.tier,c.shadow_trade,o.horizon_minutes,
                   COUNT(*) AS samples,
                   AVG(o.net_return_pct) AS avg_net_return_pct,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY o.net_return_pct) AS median_net_return_pct,
                   AVG(CASE WHEN o.net_return_pct > 0 THEN 1.0 ELSE 0.0 END) AS win_rate,
                   MIN(o.net_return_pct) AS worst_net_return_pct,
                   MAX(o.net_return_pct) AS best_net_return_pct,
                   CASE WHEN ABS(SUM(CASE WHEN o.net_return_pct < 0 THEN o.net_return_pct ELSE 0 END)) > 0
                        THEN SUM(CASE WHEN o.net_return_pct > 0 THEN o.net_return_pct ELSE 0 END)
                             / ABS(SUM(CASE WHEN o.net_return_pct < 0 THEN o.net_return_pct ELSE 0 END))
                        ELSE NULL END AS profit_factor
            FROM research_outcomes o
            JOIN research_candidates c ON c.id=o.candidate_id
            GROUP BY c.strategy,c.tier,c.shadow_trade,o.horizon_minutes
            ORDER BY c.strategy,c.tier,o.horizon_minutes
            """
        )
    return [dict(r) for r in rows]

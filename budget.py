import os
from datetime import datetime, timezone

from db import connection

# Helius free tier currently provides 1M credits/month. Keep a safety margin so
# the experiment cannot silently run into a paid tier or exhaust the project.
MONTHLY_CREDIT_BUDGET = int(os.getenv("MONTHLY_CREDIT_BUDGET", "900000"))
DAILY_CREDIT_BUDGET = int(os.getenv("DAILY_CREDIT_BUDGET", "32000"))

# Helius documents standard RPC calls as 1 credit, with archival calls at 10.
# Keep this mapping intentionally conservative and easy to audit.
ARCHIVAL_METHODS = {
    "getTransaction",
    "getBlock",
    "getBlocks",
    "getSignaturesForAddress",  # charged conservatively here even if cheaper
}


def estimate_credits(method: str) -> int:
    if method in ARCHIVAL_METHODS:
        return 10
    if method in {"getProgramAccounts", "getAsset", "getAssetsByOwner"}:
        return 10
    return 1


async def ensure_budget_schema():
    async with connection() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rpc_usage (
                id BIGSERIAL PRIMARY KEY,
                observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                method TEXT NOT NULL,
                estimated_credits INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rpc_usage_time
                ON rpc_usage(observed_at DESC);
            """
        )


async def record_rpc_usage(method: str, credits: int):
    async with connection() as conn:
        await conn.execute(
            "INSERT INTO rpc_usage(method, estimated_credits) VALUES($1,$2)",
            method,
            int(credits),
        )


async def usage_summary():
    async with connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
              COALESCE(SUM(estimated_credits) FILTER (WHERE observed_at >= date_trunc('day', NOW())), 0) AS today,
              COALESCE(SUM(estimated_credits) FILTER (WHERE observed_at >= date_trunc('month', NOW())), 0) AS month,
              COUNT(*) FILTER (WHERE observed_at >= date_trunc('day', NOW())) AS calls_today
            FROM rpc_usage
            """
        )
    today = int(row["today"])
    month = int(row["month"])
    return {
        "estimated_credits_today": today,
        "estimated_credits_month": month,
        "calls_today": int(row["calls_today"]),
        "daily_budget": DAILY_CREDIT_BUDGET,
        "monthly_budget": MONTHLY_CREDIT_BUDGET,
        "daily_remaining": max(0, DAILY_CREDIT_BUDGET - today),
        "monthly_remaining": max(0, MONTHLY_CREDIT_BUDGET - month),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


async def assert_budget_available(next_credits: int):
    usage = await usage_summary()
    if usage["estimated_credits_today"] + next_credits > DAILY_CREDIT_BUDGET:
        raise RuntimeError("Daily Helius research credit budget reached")
    if usage["estimated_credits_month"] + next_credits > MONTHLY_CREDIT_BUDGET:
        raise RuntimeError("Monthly Helius research credit budget reached")
    return usage

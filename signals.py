from collections import defaultdict
from datetime import timedelta

from db import create_signal_event, recent_received_tokens, signal_exists_recently

# Common quote / base assets we do not want to treat as accumulation targets.
IGNORE_MINTS = {
    "So11111111111111111111111111111111111111112",  # wrapped SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD2Q9S7D3Yj5YVyn8FcJ9m",   # USDT
}


async def scan_convergence(window_minutes: int = 30, min_wallets: int = 3):
    rows = await recent_received_tokens(window_minutes)
    by_mint = defaultdict(lambda: {"wallets": set(), "events": []})

    for row in rows:
        wallet = row.get("wallet")
        mint = row.get("mint")
        delta = row.get("delta")
        if not wallet or not mint or mint in IGNORE_MINTS:
            continue
        try:
            delta = float(delta)
        except (TypeError, ValueError):
            continue
        if delta <= 0:
            continue
        bucket = by_mint[mint]
        bucket["wallets"].add(wallet)
        bucket["events"].append({
            "wallet": wallet,
            "delta": delta,
            "block_time": row.get("block_time").isoformat() if row.get("block_time") else None,
            "signature": row.get("signature"),
        })

    created = []
    for mint, bucket in by_mint.items():
        wallet_count = len(bucket["wallets"])
        if wallet_count < min_wallets:
            continue
        if await signal_exists_recently("wallet_convergence_v1", mint, window_minutes):
            continue

        confidence = min(0.95, 0.35 + 0.12 * wallet_count)
        payload = {
            "window_minutes": window_minutes,
            "wallet_count": wallet_count,
            "events": bucket["events"][-20:],
            "research_only": True,
        }
        signal_id = await create_signal_event(
            signal_name="wallet_convergence_v1",
            mint=mint,
            direction="long_candidate",
            confidence=confidence,
            payload=payload,
        )
        created.append({
            "id": signal_id,
            "mint": mint,
            "wallet_count": wallet_count,
            "confidence": confidence,
        })

    return created

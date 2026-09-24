import asyncio
import logging
from datetime import datetime, timezone

import httpx

from db import (
    due_signal_outcomes,
    record_signal_outcome,
    set_signal_reference_price_if_missing,
)

log = logging.getLogger("signal-engine.evaluator")
JUPITER_PRICE_URL = "https://api.jup.ag/price/v2"
HORIZONS_MINUTES = (5, 15, 60, 360, 1440)


async def fetch_prices(mints):
    ids = sorted({m for m in mints if m})
    if not ids:
        return {}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(JUPITER_PRICE_URL, params={"ids": ",".join(ids)})
        response.raise_for_status()
        body = response.json()
    result = {}
    for mint, item in (body.get("data") or {}).items():
        try:
            result[mint] = float(item.get("price"))
        except (TypeError, ValueError, AttributeError):
            continue
    return result


async def evaluate_due_signals():
    rows = await due_signal_outcomes(HORIZONS_MINUTES, limit=100)
    if not rows:
        return {"checked": 0, "recorded": 0}

    prices = await fetch_prices([r["mint"] for r in rows])
    recorded = 0
    now = datetime.now(timezone.utc)

    for row in rows:
        price = prices.get(row["mint"])
        if price is None:
            continue

        reference = row.get("reference_price")
        if reference is None:
            # First available post-signal market price becomes the prospective
            # baseline. This is intentionally recorded contemporaneously; no
            # future backfilling is used for forward-test results.
            await set_signal_reference_price_if_missing(row["signal_id"], price)
            reference = price

        horizon = int(row["horizon_minutes"])
        raw_return_pct = ((price / float(reference)) - 1.0) * 100.0 if reference else None

        # Conservative friction allowance. This is not claimed to be exact
        # execution cost; it prevents small apparent edges from being treated
        # as economically meaningful during screening.
        assumed_round_trip_cost_bps = 60.0
        net_return_pct = None
        if raw_return_pct is not None:
            net_return_pct = raw_return_pct - (assumed_round_trip_cost_bps / 100.0)

        await record_signal_outcome(
            signal_event_id=row["signal_id"],
            horizon_minutes=horizon,
            measured_at=now,
            price=price,
            raw_return_pct=raw_return_pct,
            assumed_cost_bps=assumed_round_trip_cost_bps,
            net_return_pct=net_return_pct,
        )
        recorded += 1

    return {"checked": len(rows), "recorded": recorded}


async def evaluator_loop(state):
    await asyncio.sleep(30)
    while True:
        try:
            result = await evaluate_due_signals()
            state["evaluator_ok"] = True
            state["last_evaluation"] = datetime.now(timezone.utc).isoformat()
            state["last_evaluation_result"] = result
            if result["recorded"]:
                log.info("Recorded %s signal outcome measurements", result["recorded"])
        except Exception as exc:
            state["evaluator_ok"] = False
            state["last_error"] = repr(exc)
            log.exception("Signal outcome evaluation failed")
        await asyncio.sleep(60)

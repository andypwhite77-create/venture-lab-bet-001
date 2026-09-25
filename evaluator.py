import asyncio
import logging
from datetime import datetime, timezone

from db import (
    due_signal_outcomes,
    record_signal_outcome,
)
from marketdata import fetch_prices
from research_db import due_candidate_outcomes, record_candidate_outcome

log = logging.getLogger("signal-engine.evaluator")
SIGNAL_HORIZONS_MINUTES = (5, 15, 60, 360, 1440)
RESEARCH_HORIZONS_MINUTES = (5, 15, 30, 60, 240, 720, 1440)


async def evaluate_due_signals():
    rows = await due_signal_outcomes(SIGNAL_HORIZONS_MINUTES, limit=100)
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
            # Do not invent a historical entry price at the first outcome horizon.
            # New signals record a contemporaneous reference at creation time.
            continue
        raw = ((price / float(reference)) - 1.0) * 100.0 if reference else None
        cost_bps = 60.0
        net = raw - (cost_bps / 100.0) if raw is not None else None
        await record_signal_outcome(
            signal_event_id=row["signal_id"],
            horizon_minutes=int(row["horizon_minutes"]),
            measured_at=now,
            price=price,
            raw_return_pct=raw,
            assumed_cost_bps=cost_bps,
            net_return_pct=net,
        )
        recorded += 1
    return {"checked": len(rows), "recorded": recorded}


async def evaluate_due_research():
    rows = await due_candidate_outcomes(RESEARCH_HORIZONS_MINUTES, limit=200)
    if not rows:
        return {"checked": 0, "recorded": 0}
    prices = await fetch_prices([r["mint"] for r in rows])
    recorded = 0
    now = datetime.now(timezone.utc)
    for row in rows:
        price = prices.get(row["mint"])
        entry = row.get("entry_price")
        if price is None or not entry:
            continue
        direction = row.get("direction") or "long"
        raw = ((price / float(entry)) - 1.0) * 100.0
        if direction == "short":
            raw = -raw
        cost_bps = float(row.get("assumed_cost_bps") or 80.0)
        net = raw - (cost_bps / 100.0)
        await record_candidate_outcome(
            candidate_id=row["candidate_id"],
            horizon_minutes=int(row["horizon_minutes"]),
            measured_at=now,
            price=price,
            raw_return_pct=raw,
            assumed_cost_bps=cost_bps,
            net_return_pct=net,
        )
        recorded += 1
    return {"checked": len(rows), "recorded": recorded}


async def evaluator_loop(state):
    await asyncio.sleep(30)
    while True:
        try:
            signals = await evaluate_due_signals()
            research = await evaluate_due_research()
            state["evaluator_ok"] = True
            state["last_evaluation"] = datetime.now(timezone.utc).isoformat()
            state["last_evaluation_result"] = {"signals": signals, "research": research}
            if signals["recorded"] or research["recorded"]:
                log.info(
                    "Outcome measurements signal=%s research=%s",
                    signals["recorded"], research["recorded"],
                )
        except Exception as exc:
            state["evaluator_ok"] = False
            state["last_error"] = repr(exc)
            log.exception("Outcome evaluation failed")
        await asyncio.sleep(60)

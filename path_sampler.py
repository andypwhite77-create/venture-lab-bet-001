import asyncio
import logging
from datetime import datetime, timezone

from marketdata import fetch_prices
from research_db import active_shadow_candidates, record_price_path

log = logging.getLogger("signal-engine.path-sampler")


async def sample_active_paths():
    rows = await active_shadow_candidates(max_age_minutes=240)
    if not rows:
        return {"active": 0, "recorded": 0, "missing": 0, "coverage_ratio": None}
    # Unique mints reduce duplicate provider work and avoid exacerbating 429s.
    mints=list(dict.fromkeys(r["mint"] for r in rows))
    prices = await fetch_prices(mints)
    recorded = 0
    for row in rows:
        price = prices.get(row["mint"])
        if price is None:
            continue
        await record_price_path(row["id"], price)
        recorded += 1
    return {"active": len(rows), "recorded": recorded, "missing": len(rows)-recorded, "coverage_ratio": round(recorded/len(rows),4), "distinct_mints": len(mints), "missing_mints": [m for m in mints if m not in prices][:25]}


async def path_sampler_loop(state):
    await asyncio.sleep(50)
    while True:
        try:
            result = await sample_active_paths()
            state["path_sampler_ok"] = result["active"] == 0 or result["recorded"] > 0
            state["last_path_sample"] = datetime.now(timezone.utc).isoformat()
            state["last_path_result"] = result
        except Exception as exc:
            state["path_sampler_ok"] = False
            state["last_error"] = repr(exc)
            log.exception("Candidate price-path sampling failed")
        await asyncio.sleep(60)

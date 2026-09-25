import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from budget import (
    assert_budget_available,
    ensure_budget_schema,
    estimate_credits,
    record_rpc_usage,
    usage_summary,
)
from collector import discover_from_jupiter
from db import (
    counts,
    init_db,
    outcome_summary,
    recent_outcomes,
    recent_signals,
    recent_wallets,
    record_event,
    record_rpc_sample,
)
from evaluator import evaluate_due_signals, evaluator_loop
from monitoring import health_alerts, send_telegram, telegram_enabled
from signals import scan_convergence

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("signal-engine")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Venture Lab Bet 001", version="0.6.0")

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
PAPER_TRADING_ONLY = os.getenv("PAPER_TRADING_ONLY", "true").lower() == "true"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}" if HELIUS_API_KEY else ""

state = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "last_rpc_check": None,
    "latest_slot": None,
    "rpc_ok": False,
    "db_ok": False,
    "collector_ok": False,
    "signal_scanner_ok": False,
    "evaluator_ok": False,
    "last_collection": None,
    "last_collection_result": None,
    "last_signal_scan": None,
    "last_signal_result": None,
    "last_evaluation": None,
    "last_evaluation_result": None,
    "last_error": None,
    "paper_trading_only": PAPER_TRADING_ONLY,
    "telegram_enabled": telegram_enabled(),
    "active_alerts": [],
}


async def rpc_call(method: str, params=None):
    if not RPC_URL:
        raise RuntimeError("HELIUS_API_KEY is not configured")

    estimated = estimate_credits(method)
    if state["db_ok"]:
        await assert_budget_available(estimated)

    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(RPC_URL, json=payload)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(str(body["error"]))

    if state["db_ok"]:
        await record_rpc_usage(method, estimated)
    return body.get("result")


async def heartbeat():
    while True:
        try:
            slot = await rpc_call("getSlot")
            state["latest_slot"] = slot
            state["last_rpc_check"] = datetime.now(timezone.utc).isoformat()
            state["rpc_ok"] = True
            state["last_error"] = None
            if state["db_ok"]:
                await record_rpc_sample(slot)
            log.info("Helius RPC healthy; latest slot=%s", slot)
        except Exception as exc:
            state["rpc_ok"] = False
            state["last_error"] = repr(exc)
            state["last_rpc_check"] = datetime.now(timezone.utc).isoformat()
            log.exception("Helius RPC heartbeat failed")
        await asyncio.sleep(60)


async def collection_loop():
    await asyncio.sleep(5)
    while True:
        try:
            result = await discover_from_jupiter(rpc_call, log, batch_size=3)
            state["collector_ok"] = True
            state["last_collection"] = datetime.now(timezone.utc).isoformat()
            state["last_collection_result"] = result
            state["last_error"] = None
        except Exception as exc:
            state["collector_ok"] = False
            state["last_error"] = repr(exc)
            log.exception("Wallet discovery cycle failed")
            try:
                await record_event("error", "collector_failure", str(exc))
            except Exception:
                pass
        await asyncio.sleep(60)


async def signal_loop():
    await asyncio.sleep(20)
    while True:
        try:
            created = await scan_convergence(window_minutes=30, min_wallets=3)
            state["signal_scanner_ok"] = True
            state["last_signal_scan"] = datetime.now(timezone.utc).isoformat()
            state["last_signal_result"] = {"created": len(created), "signals": created}
            state["last_error"] = None
            if created:
                await record_event("info", "signal_created", f"Created {len(created)} convergence signal(s)", {"signals": created})
                log.info("Created %s convergence signal(s)", len(created))
                if telegram_enabled():
                    await send_telegram(
                        "Venture Lab: new convergence signal(s)\n"
                        f"Created: {len(created)}\n"
                        "Research/paper mode only."
                    )
        except Exception as exc:
            state["signal_scanner_ok"] = False
            state["last_error"] = repr(exc)
            log.exception("Signal scan failed")
            try:
                await record_event("error", "signal_scan_failure", str(exc))
            except Exception:
                pass
        await asyncio.sleep(120)


async def monitoring_loop():
    await asyncio.sleep(45)
    previous = set()
    while True:
        try:
            budget = await usage_summary() if state["db_ok"] else None
            alerts = health_alerts(state, budget)
            state["active_alerts"] = alerts
            current = set(alerts)
            new_alerts = current - previous
            if new_alerts and telegram_enabled():
                await send_telegram("Venture Lab alert\n" + "\n".join(f"• {a}" for a in sorted(new_alerts)))
            previous = current
        except Exception as exc:
            log.warning("Monitoring loop failed: %r", exc)
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    if not PAPER_TRADING_ONLY:
        raise RuntimeError("Research build refuses to start unless PAPER_TRADING_ONLY=true")
    try:
        await init_db()
        state["db_ok"] = True
        await ensure_budget_schema()
        await record_event("info", "startup", "Signal engine research build started", {"version": "0.6.0"})
    except Exception as exc:
        state["db_ok"] = False
        state["last_error"] = repr(exc)
        log.exception("Database initialization failed")
        raise

    asyncio.create_task(heartbeat())
    asyncio.create_task(collection_loop())
    asyncio.create_task(signal_loop())
    asyncio.create_task(evaluator_loop(state))
    asyncio.create_task(monitoring_loop())
    log.info("Signal engine v0.6 started in paper-trading-only mode")

    if telegram_enabled():
        try:
            await send_telegram("Venture Lab signal engine v0.6 started — paper/research mode only.")
        except Exception as exc:
            log.warning("Startup Telegram notification failed: %r", exc)


@app.get("/health")
async def health():
    ok = state["rpc_ok"] and state["db_ok"]
    return {
        "ok": ok,
        "rpc_ok": state["rpc_ok"],
        "db_ok": state["db_ok"],
        "collector_ok": state["collector_ok"],
        "signal_scanner_ok": state["signal_scanner_ok"],
        "evaluator_ok": state["evaluator_ok"],
        "paper_trading_only": PAPER_TRADING_ONLY,
    }


@app.get("/status")
async def status():
    snapshot = dict(state)
    if state["db_ok"]:
        snapshot["counts"] = await counts()
        snapshot["rpc_budget"] = await usage_summary()
        snapshot["outcome_summary"] = await outcome_summary()
    return snapshot


@app.get("/monitoring")
async def monitoring_status():
    budget = await usage_summary() if state["db_ok"] else None
    return {
        "healthy": bool(state["rpc_ok"] and state["db_ok"] and not state["active_alerts"]),
        "telegram_enabled": telegram_enabled(),
        "alerts": health_alerts(state, budget),
        "counts": await counts() if state["db_ok"] else {},
        "budget": budget,
        "last_collection": state["last_collection"],
        "last_signal_scan": state["last_signal_scan"],
        "last_evaluation": state["last_evaluation"],
        "latest_slot": state["latest_slot"],
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return """<!doctype html>
<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Venture Lab</title>
<style>body{font-family:system-ui;margin:24px;background:#10131a;color:#e8edf5}pre{white-space:pre-wrap;background:#171c26;padding:16px;border-radius:12px}h1{font-size:22px}</style>
</head><body><h1>Venture Lab — Research Engine</h1><p>Paper-trading mode. Auto-refreshes every 15 seconds.</p><pre id='out'>Loading…</pre>
<script>async function go(){try{let r=await fetch('/monitoring');let j=await r.json();document.getElementById('out').textContent=JSON.stringify(j,null,2)}catch(e){document.getElementById('out').textContent=String(e)}}go();setInterval(go,15000)</script></body></html>"""


@app.get("/budget")
async def budget_status():
    return await usage_summary()


@app.get("/wallets/recent")
async def wallets_recent(limit: int = 20):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return {"wallets": await recent_wallets(limit)}


@app.get("/signals/recent")
async def signals_recent(limit: int = 20):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return {"signals": await recent_signals(limit)}


@app.get("/outcomes/recent")
async def outcomes_recent(limit: int = 50):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    return {"outcomes": await recent_outcomes(limit)}


@app.get("/outcomes/summary")
async def outcomes_summary_endpoint():
    return {"summary": await outcome_summary()}


@app.get("/rpc-check")
async def rpc_check():
    slot = await rpc_call("getSlot")
    return {"ok": True, "latest_slot": slot}


@app.post("/collector/run-once")
async def collector_run_once():
    if not PAPER_TRADING_ONLY:
        raise HTTPException(status_code=403, detail="research guard disabled")
    result = await discover_from_jupiter(rpc_call, log, batch_size=3)
    return {"ok": True, **result}


@app.post("/signals/run-once")
async def signals_run_once():
    if not PAPER_TRADING_ONLY:
        raise HTTPException(status_code=403, detail="research guard disabled")
    created = await scan_convergence(window_minutes=30, min_wallets=3)
    return {"ok": True, "created": created}


@app.post("/outcomes/run-once")
async def outcomes_run_once():
    if not PAPER_TRADING_ONLY:
        raise HTTPException(status_code=403, detail="research guard disabled")
    return {"ok": True, **(await evaluate_due_signals())}

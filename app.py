import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx
from rpc_provider import rpc_call as provider_rpc_call, configured as rpc_configured
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
from evaluator import evaluate_due_research, evaluate_due_signals, evaluator_loop
from monitoring import health_alerts, send_telegram, telegram_enabled
from path_sampler import path_sampler_loop, sample_active_paths
from signals import scan_convergence
from research import research_loop, run_research_cycle
from research_db import ensure_research_schema, price_path_counts, recent_candidates, research_counts, research_scoreboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("signal-engine")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Venture Lab Bet 001", version="1.0.0")

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
PAPER_TRADING_ONLY = os.getenv("PAPER_TRADING_ONLY", "true").lower() == "true"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}" if HELIUS_API_KEY else ""

state = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "last_rpc_check": None,
    "latest_slot": None,
    "rpc_ok": False,
    "rpc_provider": None,
    "rpc_configured": rpc_configured(),
    "db_ok": False,
    "collector_ok": False,
    "signal_scanner_ok": False,
    "evaluator_ok": False,
    "research_ok": False,
    "path_sampler_ok": False,
    "last_collection": None,
    "last_collection_result": None,
    "last_signal_scan": None,
    "last_signal_result": None,
    "last_evaluation": None,
    "last_evaluation_result": None,
    "last_research_cycle": None,
    "last_research_result": None,
    "last_path_sample": None,
    "last_path_result": None,
    "last_error": None,
    "paper_trading_only": PAPER_TRADING_ONLY,
    "telegram_enabled": telegram_enabled(),
    "active_alerts": [],
}


async def rpc_call(method: str, params=None):
    result, provider = await provider_rpc_call(method, params, db_ok=state["db_ok"])
    state["rpc_provider"] = provider
    return result


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
            log.info("Solana RPC healthy provider=%s latest slot=%s", state.get("rpc_provider"), slot)
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
        await ensure_research_schema()
        await record_event("info", "startup", "Venture Lab multi-strategy research engine started", {"version": "1.0.0"})
    except Exception as exc:
        state["db_ok"] = False
        state["last_error"] = repr(exc)
        log.exception("Database initialization failed")
        raise

    asyncio.create_task(heartbeat())
    asyncio.create_task(collection_loop())
    asyncio.create_task(signal_loop())
    asyncio.create_task(evaluator_loop(state))
    asyncio.create_task(research_loop(state))
    asyncio.create_task(path_sampler_loop(state))
    asyncio.create_task(monitoring_loop())
    log.info("Venture Lab v1.0 multi-strategy research engine started in shadow mode")

    if telegram_enabled():
        try:
            await send_telegram("Venture Lab v1.0 research engine started — shadow/paper mode only.")
        except Exception as exc:
            log.warning("Startup Telegram notification failed: %r", exc)


@app.get("/health")
async def health():
    ok = all(state[k] for k in (
        "rpc_ok", "db_ok", "collector_ok", "signal_scanner_ok",
        "evaluator_ok", "research_ok", "path_sampler_ok",
    ))
    return {
        "ok": ok,
        "rpc_ok": state["rpc_ok"],
        "db_ok": state["db_ok"],
        "collector_ok": state["collector_ok"],
        "signal_scanner_ok": state["signal_scanner_ok"],
        "evaluator_ok": state["evaluator_ok"],
        "research_ok": state["research_ok"],
        "path_sampler_ok": state["path_sampler_ok"],
        "paper_trading_only": PAPER_TRADING_ONLY,
    }


@app.get("/status")
async def status():
    snapshot = dict(state)
    if state["db_ok"]:
        snapshot["counts"] = await counts()
        snapshot["rpc_budget"] = await usage_summary()
        snapshot["outcome_summary"] = await outcome_summary()
        snapshot["research_counts"] = await research_counts()
        snapshot["research_scoreboard"] = await research_scoreboard()
        snapshot["price_path_counts"] = await price_path_counts()
    return snapshot


@app.get("/monitoring")
async def monitoring_status():
    budget = await usage_summary() if state["db_ok"] else None
    alerts = health_alerts(state, budget)
    components_ok = all(state[k] for k in (
        "rpc_ok", "db_ok", "collector_ok", "signal_scanner_ok",
        "evaluator_ok", "research_ok", "path_sampler_ok",
    ))
    return {
        "healthy": bool(components_ok and not alerts),
        "telegram_enabled": telegram_enabled(),
        "alerts": alerts,
        "counts": await counts() if state["db_ok"] else {},
        "budget": budget,
        "last_collection": state["last_collection"],
        "last_signal_scan": state["last_signal_scan"],
        "last_evaluation": state["last_evaluation"],
        "last_research_cycle": state["last_research_cycle"],
        "latest_slot": state["latest_slot"],
    }


@app.get("/colony/live")
async def colony_live():
    from colony.dashboard_api import snapshot
    return await snapshot()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    from pathlib import Path
    return HTMLResponse(Path("colony/dashboard.html").read_text())

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
    return {"ok": True, "signals": await evaluate_due_signals(), "research": await evaluate_due_research()}


@app.post("/research/run-once")
async def research_run_once():
    if not PAPER_TRADING_ONLY:
        raise HTTPException(status_code=403, detail="research guard disabled")
    return {"ok": True, **(await run_research_cycle())}


@app.get("/research/candidates")
async def research_candidates(limit: int = 50, shadow_only: bool = False):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    return {"candidates": await recent_candidates(limit, shadow_only)}


@app.get("/research/scoreboard")
async def research_scoreboard_endpoint():
    return {"counts": await research_counts(), "scoreboard": await research_scoreboard()}


@app.post("/research/sample-paths")
async def research_sample_paths():
    if not PAPER_TRADING_ONLY:
        raise HTTPException(status_code=403, detail="research guard disabled")
    return {"ok": True, **(await sample_active_paths())}

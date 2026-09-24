import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException

from collector import discover_from_jupiter
from db import counts, init_db, recent_wallets, record_event, record_rpc_sample

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("signal-engine")

app = FastAPI(title="Venture Lab Bet 001", version="0.2.0")

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
    "last_collection": None,
    "last_collection_result": None,
    "last_error": None,
    "paper_trading_only": PAPER_TRADING_ONLY,
}


async def rpc_call(method: str, params=None):
    if not RPC_URL:
        raise RuntimeError("HELIUS_API_KEY is not configured")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }
    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(RPC_URL, json=payload)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(str(body["error"]))
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
            result = await discover_from_jupiter(rpc_call, log, batch_size=2)
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


@app.on_event("startup")
async def startup_event():
    if not PAPER_TRADING_ONLY:
        raise RuntimeError("Research build refuses to start unless PAPER_TRADING_ONLY=true")
    try:
        await init_db()
        state["db_ok"] = True
        await record_event("info", "startup", "Signal engine research build started")
    except Exception as exc:
        state["db_ok"] = False
        state["last_error"] = repr(exc)
        log.exception("Database initialization failed")
        raise

    asyncio.create_task(heartbeat())
    asyncio.create_task(collection_loop())
    log.info("Signal engine v0.2 started in paper-trading-only mode")


@app.get("/health")
async def health():
    ok = state["rpc_ok"] and state["db_ok"]
    return {
        "ok": ok,
        "rpc_ok": state["rpc_ok"],
        "db_ok": state["db_ok"],
        "collector_ok": state["collector_ok"],
        "paper_trading_only": PAPER_TRADING_ONLY,
    }


@app.get("/status")
async def status():
    snapshot = dict(state)
    if state["db_ok"]:
        snapshot["counts"] = await counts()
    return snapshot


@app.get("/wallets/recent")
async def wallets_recent(limit: int = 20):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return {"wallets": await recent_wallets(limit)}


@app.get("/rpc-check")
async def rpc_check():
    slot = await rpc_call("getSlot")
    return {"ok": True, "latest_slot": slot}


@app.post("/collector/run-once")
async def collector_run_once():
    if not PAPER_TRADING_ONLY:
        raise HTTPException(status_code=403, detail="research guard disabled")
    result = await discover_from_jupiter(rpc_call, log, batch_size=2)
    return {"ok": True, **result}

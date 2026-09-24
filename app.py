import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("signal-engine")

app = FastAPI(title="Venture Lab Bet 001", version="0.1.0")

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
PAPER_TRADING_ONLY = os.getenv("PAPER_TRADING_ONLY", "true").lower() == "true"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}" if HELIUS_API_KEY else ""

state = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "last_rpc_check": None,
    "latest_slot": None,
    "rpc_ok": False,
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
    async with httpx.AsyncClient(timeout=20.0) as client:
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
            log.info("Helius RPC healthy; latest slot=%s", slot)
        except Exception as exc:
            state["rpc_ok"] = False
            state["last_error"] = repr(exc)
            state["last_rpc_check"] = datetime.now(timezone.utc).isoformat()
            log.exception("Helius RPC heartbeat failed")
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    if not PAPER_TRADING_ONLY:
        raise RuntimeError("Research build refuses to start unless PAPER_TRADING_ONLY=true")
    asyncio.create_task(heartbeat())
    log.info("Signal engine started in paper-trading-only mode")


@app.get("/health")
async def health():
    return {
        "ok": True,
        "rpc_ok": state["rpc_ok"],
        "paper_trading_only": PAPER_TRADING_ONLY,
    }


@app.get("/status")
async def status():
    return state


@app.get("/rpc-check")
async def rpc_check():
    slot = await rpc_call("getSlot")
    return {"ok": True, "latest_slot": slot}

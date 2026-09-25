import asyncio
import logging

import httpx

log = logging.getLogger("signal-engine.marketdata")
GECKO_MULTI_URL = "https://api.geckoterminal.com/api/v2/networks/solana/tokens/multi/{addresses}"
GECKO_TRENDING_URL = "https://api.geckoterminal.com/api/v2/networks/solana/trending_pools?page=1"
MAX_MULTI = 30


def _f(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _i(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _rel_id(item, name):
    try:
        return item["relationships"][name]["data"]["id"]
    except (KeyError, TypeError):
        return ""


def normalize_token(item: dict) -> dict:
    a = item.get("attributes") or {}
    mint = a.get("address") or (item.get("id") or "").replace("solana_", "")
    return {
        "mint": mint,
        "symbol": a.get("symbol"),
        "pair_address": None,
        "dex_id": None,
        "price_usd": _f(a.get("price_usd")),
        "liquidity_usd": _f(a.get("total_reserve_in_usd"), 0.0),
        "fdv": _f(a.get("fdv_usd")),
        "market_cap": _f(a.get("market_cap_usd")),
        "volume_m5": 0.0,
        "volume_h1": 0.0,
        "price_change_m5": 0.0,
        "price_change_h1": 0.0,
        "buys_m5": 0,
        "sells_m5": 0,
        "buys_h1": 0,
        "sells_h1": 0,
        "pair_created_at": None,
        "source": "geckoterminal_token_multi",
    }


def normalize_trending_pool(pool: dict) -> dict:
    a = pool.get("attributes") or {}
    base_id = _rel_id(pool, "base_token")
    mint = base_id.replace("solana_", "")
    txns = a.get("transactions") or {}
    m5_txns = txns.get("m5") or {}
    h1_txns = txns.get("h1") or {}
    volume = a.get("volume_usd") or {}
    change = a.get("price_change_percentage") or {}
    name = a.get("name") or ""
    return {
        "mint": mint,
        "symbol": name.split(" / ")[0] if name else None,
        "pair_address": a.get("address"),
        "dex_id": _rel_id(pool, "dex").replace("solana_", ""),
        "price_usd": _f(a.get("base_token_price_usd")),
        "liquidity_usd": _f(a.get("reserve_in_usd"), 0.0),
        "fdv": _f(a.get("fdv_usd")),
        "market_cap": _f(a.get("market_cap_usd")),
        "volume_m5": _f(volume.get("m5"), 0.0),
        "volume_h1": _f(volume.get("h1"), 0.0),
        "price_change_m5": _f(change.get("m5"), 0.0),
        "price_change_h1": _f(change.get("h1"), 0.0),
        "buys_m5": _i(m5_txns.get("buys")),
        "sells_m5": _i(m5_txns.get("sells")),
        "buys_h1": _i(h1_txns.get("buys")),
        "sells_h1": _i(h1_txns.get("sells")),
        "pair_created_at": a.get("pool_created_at"),
        "source": "geckoterminal_trending",
    }


async def _get_json(url: str, attempts: int = 3):
    headers = {"User-Agent": "Mozilla/5.0 venture-lab-research", "Accept": "application/json"}
    last_exc = None
    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json() or {}
        except Exception as exc:
            last_exc = exc
            if attempt + 1 < attempts:
                await asyncio.sleep(1.0 * (2 ** attempt))
    raise last_exc


async def fetch_market_snapshots(mints) -> dict[str, dict]:
    ids = sorted({m for m in mints if m})
    if not ids:
        return {}
    result = {}
    for offset in range(0, len(ids), MAX_MULTI):
        chunk = ids[offset:offset + MAX_MULTI]
        try:
            body = await _get_json(GECKO_MULTI_URL.format(addresses=",".join(chunk)))
            rows = [normalize_token(item) for item in (body.get("data") or [])]
            result.update({row["mint"]: row for row in rows if row.get("mint") and row.get("price_usd")})
        except Exception as exc:
            log.warning("Token multi-market snapshot failed after retries: %r", exc)
    return result


async def fetch_trending_market_snapshots(limit: int = 20) -> dict[str, dict]:
    try:
        body = await _get_json(GECKO_TRENDING_URL)
        pools = body.get("data") or []
        rows = [normalize_trending_pool(pool) for pool in pools[:limit]]
        return {row["mint"]: row for row in rows if row.get("mint") and row.get("price_usd")}
    except Exception as exc:
        log.warning("Trending market snapshot failed after retries: %r", exc)
        return {}


async def fetch_prices(mints) -> dict[str, float]:
    snapshots = await fetch_market_snapshots(mints)
    return {mint: snap["price_usd"] for mint, snap in snapshots.items() if snap.get("price_usd") is not None}

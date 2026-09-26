import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from marketdata import fetch_market_snapshots, fetch_trending_market_snapshots
from research_db import candidate_exists_recently, create_candidate, recent_token_events, save_market_snapshot

log = logging.getLogger("signal-engine.research")

IGNORE_MINTS = {
    "So11111111111111111111111111111111111111112",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
}

STRATEGIES = {
    "wallet_convergence_v2": "A",
    "order_flow_acceleration_v1": "B",
    "liquidity_shock_reversal_v1": "C",
    "volume_momentum_v1": "D",
}


def _clip(value, lo=0.0, hi=0.99):
    return max(lo, min(hi, float(value)))


def _window_stats(rows, now):
    stats = defaultdict(lambda: {
        "buy_wallets_30": set(), "sell_wallets_30": set(),
        "buys_15": 0, "sells_15": 0, "prev_buys_15": 0, "prev_sells_15": 0,
        "buys_30": 0, "sells_30": 0, "latest": None,
    })
    for row in rows:
        mint = row.get("mint")
        wallet = row.get("wallet")
        block_time = row.get("block_time")
        if not mint or mint in IGNORE_MINTS or not block_time:
            continue
        try:
            delta = float(row.get("delta"))
        except (TypeError, ValueError):
            continue
        age = now - block_time
        s = stats[mint]
        if s["latest"] is None or block_time > s["latest"]:
            s["latest"] = block_time
        if age <= timedelta(minutes=30):
            if delta > 0:
                s["buys_30"] += 1
                if wallet:
                    s["buy_wallets_30"].add(wallet)
            elif delta < 0:
                s["sells_30"] += 1
                if wallet:
                    s["sell_wallets_30"].add(wallet)
        if age <= timedelta(minutes=15):
            if delta > 0:
                s["buys_15"] += 1
            elif delta < 0:
                s["sells_15"] += 1
        elif age <= timedelta(minutes=30):
            if delta > 0:
                s["prev_buys_15"] += 1
            elif delta < 0:
                s["prev_sells_15"] += 1
    return stats


def _features(s):
    if not s:
        return {
            "buy_wallets_30": 0, "buys_30": 0, "sells_30": 0,
            "buys_15": 0, "sells_15": 0, "prev_buys_15": 0,
            "flow_ratio_15": 0.0, "buy_acceleration": 0.0,
        }
    wallets = len(s["buy_wallets_30"])
    buys15 = s["buys_15"]
    sells15 = s["sells_15"]
    prev_buys = s["prev_buys_15"]
    return {
        "buy_wallets_30": wallets,
        "buys_30": s["buys_30"],
        "sells_30": s["sells_30"],
        "buys_15": buys15,
        "sells_15": sells15,
        "prev_buys_15": prev_buys,
        "flow_ratio_15": round(buys15 / max(1, buys15 + sells15), 4),
        "buy_acceleration": round(buys15 / max(1, prev_buys), 4),
    }


def _dex_buy_ratio(market):
    buys = int(market.get("buys_m5") or 0)
    sells = int(market.get("sells_m5") or 0)
    return buys / max(1, buys + sells)


async def _record(strategy, mint, score, tier, shadow_trade, features, market, cooldown=30):
    if await candidate_exists_recently(strategy, mint, cooldown, tier=tier):
        return None
    entry_price = market.get("price_usd") if market else None
    shadow_trade = bool(shadow_trade and entry_price and entry_price > 0)
    candidate_id = await create_candidate(
        strategy=strategy, mint=mint, direction="long", score=score, tier=tier,
        shadow_trade=shadow_trade, entry_price=entry_price,
        features=features, market=market or {}, assumed_cost_bps=80.0,
    )
    if market:
        await save_market_snapshot(mint, strategy, market)
    return {
        "id": candidate_id, "strategy": strategy, "mint": mint,
        "score": round(score, 3), "tier": tier,
        "shadow_trade": shadow_trade, "entry_price": entry_price,
    }


async def run_research_cycle():
    now = datetime.now(timezone.utc)
    rows = await recent_token_events(window_minutes=60)
    stats = _window_stats(rows, now)
    created = []

    ab_specs = []
    for mint, s in stats.items():
        f = _features(s)
        wallets = f["buy_wallets_30"]
        if wallets >= 2:
            is_trade = wallets >= 3
            score = _clip(0.35 + wallets * 0.12 + min(0.12, f["buys_30"] * 0.02))
            ab_specs.append(("wallet_convergence_v2", mint, score, "trade" if is_trade else "observe", is_trade, f, 30))

        if f["buys_15"] >= 2 and wallets >= 2 and f["flow_ratio_15"] >= 0.60:
            is_trade = f["buys_15"] >= 3 and f["flow_ratio_15"] >= 0.70 and f["buy_acceleration"] >= 1.5
            score = _clip(0.25 + 0.08 * f["buys_15"] + 0.20 * f["flow_ratio_15"] + 0.08 * min(f["buy_acceleration"], 3))
            ab_specs.append(("order_flow_acceleration_v1", mint, score, "trade" if is_trade else "observe", is_trade, f, 20))

    ab_market = await fetch_market_snapshots([spec[1] for spec in ab_specs]) if ab_specs else {}
    for strategy, mint, score, tier, is_trade, features, cooldown in ab_specs:
        item = await _record(strategy, mint, score, tier, is_trade, features, ab_market.get(mint, {}), cooldown)
        if item:
            created.append(item)

    trending = await fetch_trending_market_snapshots(limit=20)
    for mint, market in trending.items():
        if mint in IGNORE_MINTS:
            continue
        f = _features(stats.get(mint))
        liq = float(market.get("liquidity_usd") or 0.0)
        pc5 = float(market.get("price_change_m5") or 0.0)
        pc1h = float(market.get("price_change_h1") or 0.0)
        vol5 = float(market.get("volume_m5") or 0.0)
        vol_liq = vol5 / max(1.0, liq)
        dex_ratio = _dex_buy_ratio(market)
        mf = {
            **f,
            "liquidity_usd": liq,
            "price_change_m5": pc5,
            "price_change_h1": pc1h,
            "volume_m5": vol5,
            "volume_liquidity_m5": round(vol_liq, 6),
            "dex_buy_ratio_m5": round(dex_ratio, 4),
        }

        if pc5 <= -5.0 and liq >= 50_000 and dex_ratio >= 0.52:
            is_trade = pc5 <= -8.0 and liq >= 100_000 and dex_ratio >= 0.58 and pc1h > -25.0
            score = _clip(0.30 + min(abs(pc5), 20) / 50 + min(liq, 500_000) / 2_500_000 + 0.15 * dex_ratio)
            item = await _record(
                "liquidity_shock_reversal_v1", mint, score,
                "trade" if is_trade else "observe", is_trade, mf, market, 30,
            )
            if item:
                created.append(item)

        if pc5 >= 1.0 and pc1h >= 2.0 and liq >= 50_000 and vol_liq >= 0.01 and dex_ratio >= 0.55:
            is_trade = pc5 >= 3.0 and pc1h >= 5.0 and liq >= 100_000 and vol_liq >= 0.02 and dex_ratio >= 0.60
            score = _clip(0.25 + min(pc5, 15) / 60 + min(pc1h, 30) / 120 + min(vol_liq, 0.25) + 0.12 * dex_ratio)
            item = await _record(
                "volume_momentum_v1", mint, score,
                "trade" if is_trade else "observe", is_trade, mf, market, 30,
            )
            if item:
                created.append(item)

    return {
        "candidates": len(created),
        "shadow_trades": sum(1 for x in created if x["shadow_trade"]),
        "events": created,
    }


async def research_loop(state):
    await asyncio.sleep(40)
    while True:
        try:
            result = await run_research_cycle()
            state["research_ok"] = True
            state["last_research_cycle"] = datetime.now(timezone.utc).isoformat()
            state["last_research_result"] = result
            if result["candidates"]:
                log.info("Research cycle created=%s shadow_trades=%s", result["candidates"], result["shadow_trades"])
        except Exception as exc:
            state["research_ok"] = False
            state["last_error"] = repr(exc)
            log.exception("Research strategy cycle failed")
        await asyncio.sleep(60)

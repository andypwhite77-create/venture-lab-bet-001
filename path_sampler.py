import asyncio
import logging
from datetime import datetime, timezone

import marketdata
from collector_fresh_prices import fetch as fetch_fresh_prices
from collector_dexscreener import fetch as fetch_dexscreener
import time
from colony.sensors import birdeye_price,coingecko_price
from research_db import active_shadow_candidates, record_price_path

log = logging.getLogger("signal-engine.path-sampler")
# Per-provider outage gates prevent one bad provider from receiving a burst of
# redundant requests across missing tokens. This never substitutes prices.
_PROVIDER_BLOCK_UNTIL={}
def provider_allowed(provider,now=None):
    current=time.monotonic() if now is None else now
    return current>=_PROVIDER_BLOCK_UNTIL.get(provider,0)
def provider_result(provider,result,now=None):
    current=time.monotonic() if now is None else now
    error=str(result.get('error','')).lower()
    if '429' in error or 'rate_limit' in error:
        _PROVIDER_BLOCK_UNTIL[provider]=current+900
    elif '400' in error or '401' in error or '403' in error:
        _PROVIDER_BLOCK_UNTIL[provider]=current+1800
    elif error in ('no_key',):
        _PROVIDER_BLOCK_UNTIL[provider]=current+3600
    elif result.get('ok'):
        _PROVIDER_BLOCK_UNTIL.pop(provider,None)



async def sample_active_paths():
    rows = await active_shadow_candidates(max_age_minutes=240)
    if not rows:
        return {"active": 0, "recorded": 0, "missing": 0, "coverage_ratio": None}
    # Unique mints reduce duplicate provider work and avoid exacerbating 429s.
    mints=list(dict.fromkeys(r["mint"] for r in rows))
    # Snapshot caches are useful for discovery but cannot represent new ticks.
    # Clear expired Gecko entries before collection so each cycle seeks a real quote.
    prices, gecko_error = await fetch_fresh_prices(mints)
    gecko_cache={} # fresh-only endpoint bypasses discovery cache
    # A cached API response is not a new price tick. Anything older than five
    # seconds is routed to independent fallback, never relabelled fresh.
    stale_gecko={m for m in prices if m in gecko_cache and time.time()-gecko_cache[m][0]>5}
    for mint in stale_gecko:prices.pop(mint,None)
    # Provider fallback is for missing mints only. Never synthesize or reuse stale prices.
    fallback_sources={}
    failures={}
    dex_error=None
    missing=[mint for mint in mints if mint not in prices]
    if missing and provider_allowed('dexscreener'):
        dex_prices,dex_error=await fetch_dexscreener(missing)
        provider_result('dexscreener',{'ok':dex_error is None,'error':dex_error or ''})
        prices.update(dex_prices)
        fallback_sources.update({mint:'dexscreener' for mint in dex_prices})
    for mint in mints:
        if mint in prices: continue
        # CoinGecko credit allowance exhausted; exclude from collection entirely.
        for provider in (birdeye_price,):
            pname=provider.__name__
            if not provider_allowed(pname):
                failures.setdefault(mint,[]).append(pname+':cooldown')
                continue
            result=await provider(mint)
            provider_result(pname,result)
            if not result.get('ok'):
                failures.setdefault(mint,[]).append(pname+':'+str(result.get('error','unavailable')))
            if result.get('ok') and not result.get('cached',False) and result.get('price_usd') is not None:
                try:
                    candidate=float(result['price_usd'])
                    if not 0 < candidate < float('inf'):continue
                except (TypeError,ValueError,OverflowError):continue
                prices[mint]=candidate
                fallback_sources[mint]=result.get('provider',provider.__name__)
                break
    recorded = 0
    for row in rows:
        price = prices.get(row["mint"])
        if price is None:
            continue
        await record_price_path(row["id"], price, fallback_sources.get(row["mint"],"geckoterminal"), "fresh_fetch")
        recorded += 1
    return {"active": len(rows), "recorded": recorded, "missing": len(rows)-recorded, "coverage_ratio": round(recorded/len(rows),4), "distinct_mints": len(mints), "required_mints":mints, "missing_mints": [m for m in mints if m not in prices][:25], "fallback_mints":fallback_sources, "provider_failures":failures, "gecko_error":gecko_error, "dex_error":dex_error, "blocked_providers":[name for name in ("birdeye_price","coingecko_price") if not provider_allowed(name)]}


async def path_sampler_loop(state):
    await asyncio.sleep(50)
    while True:
        try:
            result = await sample_active_paths()
            state["path_sampler_ok"] = result["active"] == 0 or result["recorded"] == result["active"]
            state["last_path_sample"] = datetime.now(timezone.utc).isoformat()
            state["last_path_result"] = result
        except Exception as exc:
            state["path_sampler_ok"] = False
            state["last_error"] = repr(exc)
            log.exception("Candidate price-path sampling failed")
        await asyncio.sleep(60)

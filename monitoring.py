import os
from datetime import datetime, timezone

import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def telegram_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


async def send_telegram(message: str) -> bool:
    if not telegram_enabled():
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "disable_web_page_preview": True,
            },
        )
        response.raise_for_status()
    return True


def age_seconds(iso_timestamp):
    if not iso_timestamp:
        return None
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    except Exception:
        return None


def health_alerts(state: dict, budget: dict | None = None) -> list[str]:
    alerts = []
    if not state.get("db_ok"):
        alerts.append("Database is unhealthy")
    if not state.get("rpc_ok"):
        alerts.append("Helius RPC heartbeat is unhealthy")

    collection_age = age_seconds(state.get("last_collection"))
    if collection_age is None or collection_age > 240:
        alerts.append("Collector has not completed successfully in the last 4 minutes")

    signal_age = age_seconds(state.get("last_signal_scan"))
    if signal_age is None or signal_age > 420:
        alerts.append("Signal scanner has not completed successfully in the last 7 minutes")

    if state.get("last_error"):
        alerts.append(f"Latest engine error: {state['last_error']}")

    if budget:
        daily = budget.get("daily_budget") or 0
        monthly = budget.get("monthly_budget") or 0
        today = budget.get("estimated_credits_today") or 0
        month = budget.get("estimated_credits_month") or 0
        if daily and today / daily >= 0.8:
            alerts.append(f"Helius daily budget at {today / daily:.0%}")
        if monthly and month / monthly >= 0.8:
            alerts.append(f"Helius monthly budget at {month / monthly:.0%}")

    return alerts

"""Read-only trading analytics for the private admin control plane.

This module never mutates execution state. It normalises Canary accounting into one
stable API so browser presentation cannot redefine P&L, drawdown or promotion evidence.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

WINDOWS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "all": None,
}
ACTIVE_STATUSES = {"claimed", "open", "recovery", "submitting_entry", "submitting_exit", "uncertain"}


def _json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return dict(value or {})


def _number(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _dt(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def cutoff_for(window: str, now: datetime | None = None):
    if window not in WINDOWS:
        raise ValueError("bad_window")
    delta = WINDOWS[window]
    return None if delta is None else (now or datetime.now(timezone.utc)) - delta


def realised_pnl_sol(execution):
    e = _json(execution)
    for key in (
        "realized_market_pnl_after_network_fees_sol",
        "realized_trade_pnl_sol",
        "realized_market_pnl_sol",
    ):
        value = _number(e.get(key))
        if value is not None:
            return value
    return None


def realised_fees_sol(execution):
    e = _json(execution)
    value = _number(e.get("realized_network_fees_sol"))
    if value is not None:
        return value
    entry = _number(e.get("entry_network_fee_sol"), 0.0) or 0.0
    exit_ = _number(e.get("exit_network_fee_sol"), 0.0) or 0.0
    return entry + exit_


def trade_basis_sol(row):
    e = _json(row.get("execution"))
    return (
        _number(e.get("entry_trade_sol"))
        or _number(row.get("requested_sol"))
        or 0.0
    )


def is_realised_live_trade(row):
    e = _json(row.get("execution"))
    return (
        row.get("status") == "closed"
        and bool(row.get("broadcast"))
        and e.get("mode") == "live"
        and realised_pnl_sol(e) is not None
    )


def trade_event_at(row):
    e = _json(row.get("execution"))
    return _dt(e.get("closed_at")) or _dt(row.get("updated_at")) or _dt(row.get("created_at"))


def estimated_position(row):
    e = _json(row.get("execution"))
    basis = trade_basis_sol(row)
    quote = (
        _json(e.get("recovery_last_quote"))
        or _json(e.get("strategy_exit_quote"))
        or _json(e.get("exit_quote"))
    )
    estimate = _number(quote.get("minAmountOut"))
    if estimate is None:
        estimate = _number(quote.get("amountOut"))
    pnl = estimate - basis if estimate is not None and basis else None
    return {
        "id": row.get("id"),
        "candidate_id": row.get("candidate_id"),
        "mint": row.get("mint"),
        "status": row.get("status"),
        "hold_minutes": row.get("hold_minutes"),
        "entry_basis_sol": basis or None,
        "estimated_exit_sol": estimate,
        "estimated_pnl_sol": pnl,
        "estimated_pnl_pct": (pnl / basis * 100.0 if pnl is not None and basis else None),
        "updated_at": row.get("updated_at"),
    }


def build_trade_metrics(rows, rate: float, current_balance_sol: float | None = None):
    realised = sorted((r for r in rows if is_realised_live_trade(r)), key=lambda r: trade_event_at(r) or datetime.min.replace(tzinfo=timezone.utc))
    start_balance = _number(realised[0].get("wallet_sol")) if realised else current_balance_sol
    cumulative = 0.0
    cumulative_fees = 0.0
    wins = losses = flats = 0
    winner_sum = loser_sum = 0.0
    peak = start_balance if start_balance is not None else 0.0
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    series = []
    trades = []

    for i, row in enumerate(realised, 1):
        pnl = realised_pnl_sol(row.get("execution")) or 0.0
        fees = realised_fees_sol(row.get("execution"))
        basis = trade_basis_sol(row)
        ret = pnl / basis * 100.0 if basis else None
        cumulative += pnl
        cumulative_fees += fees
        if pnl > 0:
            wins += 1
            winner_sum += pnl
        elif pnl < 0:
            losses += 1
            loser_sum += abs(pnl)
        else:
            flats += 1
        equity = (start_balance + cumulative) if start_balance is not None else cumulative
        peak = max(peak, equity)
        drawdown = max(0.0, peak - equity)
        max_drawdown = max(max_drawdown, drawdown)
        dd_pct = (drawdown / peak * 100.0) if peak > 0 else 0.0
        max_drawdown_pct = max(max_drawdown_pct, dd_pct)
        when = trade_event_at(row)
        series.append({
            "at": when.isoformat() if when else None,
            "trade_pnl_sol": pnl,
            "trade_pnl_gbp": pnl * rate,
            "cumulative_pnl_sol": cumulative,
            "cumulative_pnl_gbp": cumulative * rate,
            "equity_sol": equity,
            "equity_gbp": equity * rate,
            "drawdown_sol": -drawdown,
            "drawdown_gbp": -drawdown * rate,
            "fees_cumulative_sol": cumulative_fees,
            "fees_cumulative_gbp": cumulative_fees * rate,
            "win_rate_pct": wins / i * 100.0,
        })
        trades.append({
            "id": row.get("id"),
            "candidate_id": row.get("candidate_id"),
            "mint": row.get("mint"),
            "closed_at": when.isoformat() if when else None,
            "stake_gbp": _number(row.get("requested_gbp")),
            "hold_minutes": row.get("hold_minutes"),
            "votes": row.get("votes"),
            "active_ants": row.get("active_ants"),
            "pnl_sol": pnl,
            "pnl_gbp": pnl * rate,
            "return_pct": ret,
            "fees_sol": fees,
            "fees_gbp": fees * rate,
        })

    count = len(realised)
    pnl_total = cumulative
    avg = pnl_total / count if count else 0.0
    best = max((x["pnl_sol"] for x in trades), default=None)
    worst = min((x["pnl_sol"] for x in trades), default=None)
    profit_factor = (winner_sum / loser_sum) if loser_sum > 0 else (None if winner_sum > 0 else 0.0)
    return {
        "summary": {
            "closed_trades": count,
            "wins": wins,
            "losses": losses,
            "flat": flats,
            "win_rate_pct": (wins / count * 100.0 if count else None),
            "realized_pnl_sol": pnl_total,
            "realized_pnl_gbp": pnl_total * rate,
            "average_trade_pnl_sol": avg,
            "average_trade_pnl_gbp": avg * rate,
            "best_trade_sol": best,
            "best_trade_gbp": (best * rate if best is not None else None),
            "worst_trade_sol": worst,
            "worst_trade_gbp": (worst * rate if worst is not None else None),
            "network_fees_sol": cumulative_fees,
            "network_fees_gbp": cumulative_fees * rate,
            "profit_factor": profit_factor,
            "max_drawdown_sol": max_drawdown,
            "max_drawdown_gbp": max_drawdown * rate,
            "max_drawdown_pct": max_drawdown_pct,
            "starting_balance_sol": start_balance,
            "current_balance_sol": current_balance_sol,
            "current_balance_gbp": (current_balance_sol * rate if current_balance_sol is not None else None),
        },
        "series": series,
        "trades": list(reversed(trades[-100:])),
    }


def paper_gate_status(forward):
    f = _json(forward)
    n = int(f.get("n") or 0)
    days = int(f.get("days") or 0)
    win = _number(f.get("win_rate"))
    median = _number(f.get("median"))
    worst = _number(f.get("worst"))
    positive_day = _number(f.get("positive_day_rate"))
    ready = (
        n >= 25 and days >= 3
        and win is not None and win >= .55
        and median is not None and median >= .25
        and worst is not None and worst >= -25
        and positive_day is not None and positive_day >= .60
    )
    return {
        "ready": ready,
        "gap_to_25": max(0, 25 - n),
        "n": n,
        "days": days,
        "mean": _number(f.get("mean")),
        "median": median,
        "win_rate": win,
        "worst": worst,
        "positive_day_rate": positive_day,
        "score": _number(f.get("score")),
    }


async def snapshot(conn, window: str, rate: float, current_balance_sol: float | None, reserve_sol: float = .003):
    cutoff = cutoff_for(window)
    if cutoff is None:
        rows = [dict(r) for r in await conn.fetch("""SELECT id,candidate_id,mint,observed_at,created_at,updated_at,status,reason,broadcast,
          votes,active_ants,vote_fraction,requested_gbp,requested_sol,wallet_sol,wallet_gbp,hold_minutes,execution
          FROM canary_trade_intents ORDER BY id""")]
    else:
        rows = [dict(r) for r in await conn.fetch("""SELECT id,candidate_id,mint,observed_at,created_at,updated_at,status,reason,broadcast,
          votes,active_ants,vote_fraction,requested_gbp,requested_sol,wallet_sol,wallet_gbp,hold_minutes,execution
          FROM canary_trade_intents WHERE updated_at >= $1 ORDER BY id""", cutoff)]

    metrics = build_trade_metrics(rows, rate, current_balance_sol)
    status_counts = {}
    rejection_reasons = {}
    for row in rows:
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == "rejected":
            reason = str(row.get("reason") or "unspecified")
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

    active_rows = [dict(r) for r in await conn.fetch("""SELECT id,candidate_id,mint,updated_at,status,hold_minutes,requested_sol,execution
      FROM canary_trade_intents WHERE status=ANY($1::text[]) ORDER BY id""", sorted(ACTIVE_STATUSES))]
    positions = [estimated_position(r) for r in active_rows]

    roster_rows = [dict(r) for r in await conn.fetch("""SELECT canary_slot,genome_id,family,source,arena_score,forward_score,total_score,
      arena_stats,forward_stats,canary_since FROM champion_league
      WHERE active=true AND canary_slot IS NOT NULL ORDER BY canary_slot""")]
    roster = []
    for row in roster_rows:
        roster.append({
            "slot": row["canary_slot"],
            "genome_id": row["genome_id"],
            "family": row["family"],
            "source": row["source"],
            "arena_score": row["arena_score"],
            "forward_score": row["forward_score"],
            "total_score": row["total_score"],
            "forward": paper_gate_status(row["forward_stats"]),
            "canary_since": row["canary_since"],
        })

    challenger_rows = [dict(r) for r in await conn.fetch("""SELECT qualification_rank,genome_id,family,source,arena_score,forward_score,total_score,
      arena_stats,forward_stats,notes FROM champion_league
      WHERE active=true AND pool='qualification' AND canary_slot IS NULL
      ORDER BY qualification_rank NULLS LAST,total_score DESC NULLS LAST LIMIT 20""")]
    challengers = []
    for row in challenger_rows:
        challengers.append({
            "rank": row["qualification_rank"],
            "genome_id": row["genome_id"],
            "family": row["family"],
            "source": row["source"],
            "arena_score": row["arena_score"],
            "forward_score": row["forward_score"],
            "total_score": row["total_score"],
            "forward": paper_gate_status(row["forward_stats"]),
            "historical_priority": _json(row["notes"]).get("historical_priority_tier"),
        })

    realised_ids = [x["id"] for x in metrics["trades"]]
    contributions = {}
    if realised_ids:
        vote_rows = await conn.fetch("""SELECT v.intent_id,v.genome_id,v.canary_slot
          FROM canary_intent_votes v WHERE v.intent_id=ANY($1::bigint[])""", realised_ids)
        trade_by_id = {x["id"]: x for x in metrics["trades"]}
        supporters = {}
        for row in vote_rows:
            supporters.setdefault(row["intent_id"], []).append(dict(row))
        for intent_id, voters in supporters.items():
            trade = trade_by_id.get(intent_id)
            if not trade or not voters:
                continue
            share = trade["pnl_gbp"] / len(voters)
            for voter in voters:
                x = contributions.setdefault(voter["genome_id"], {
                    "genome_id": voter["genome_id"], "supported_trades": 0, "wins": 0,
                    "attributed_pnl_gbp": 0.0, "last_slot": voter["canary_slot"],
                })
                x["supported_trades"] += 1
                x["wins"] += int(trade["pnl_gbp"] > 0)
                x["attributed_pnl_gbp"] += share
                x["last_slot"] = voter["canary_slot"]

    summary = metrics["summary"]
    summary["reserve_sol"] = reserve_sol
    summary["reserve_gbp"] = reserve_sol * rate
    summary["available_above_reserve_sol"] = (
        max(0.0, current_balance_sol - reserve_sol) if current_balance_sol is not None else None
    )
    summary["available_above_reserve_gbp"] = (
        summary["available_above_reserve_sol"] * rate
        if summary["available_above_reserve_sol"] is not None else None
    )

    return {
        "window": window,
        "rate_gbp_per_sol": rate,
        "summary": summary,
        "series": metrics["series"],
        "trades": metrics["trades"],
        "positions": positions,
        "status_counts": status_counts,
        "rejection_reasons": [
            {"reason": k, "count": v}
            for k, v in sorted(rejection_reasons.items(), key=lambda x: (-x[1], x[0]))
        ],
        "roster": roster,
        "challengers": challengers,
        "ant_contribution": sorted(contributions.values(), key=lambda x: x["attributed_pnl_gbp"], reverse=True),
    }

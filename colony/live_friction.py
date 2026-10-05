"""Calibrate paper proportional friction from completed live Canary trades.

The calibration compares each live intent's strategy-horizon executable quote P&L
with the paper evaluator's raw return for the same candidate and hold horizon.
This deliberately captures real routing/price-impact/latency drag while leaving
fixed network fees to paper_economics. Historical outcomes are never rewritten.
"""
from __future__ import annotations
import json, statistics

DEFAULT_BPS = 80.0
MIN_SAMPLES = 2
MAX_BPS = 1500.0
LOOKBACK = 30


def _obj(value):
    if isinstance(value, dict): return value
    if isinstance(value, str):
        try: return json.loads(value)
        except Exception: return {}
    return {}


def implied_drag_bps(raw_return_pct: float, strategy_horizon_pnl_sol: float, entry_trade_sol: float) -> float | None:
    if strategy_horizon_pnl_sol is None or not entry_trade_sol or float(entry_trade_sol) <= 0:
        return None
    live_pct = float(strategy_horizon_pnl_sol) / float(entry_trade_sol) * 100.0
    # Negative drag means live execution beat the contemporaneous paper mark;
    # do not turn that into an execution subsidy.
    return max(0.0, min(MAX_BPS, (float(raw_return_pct) - live_pct) * 100.0))


async def calibration(conn, baseline_bps: float = DEFAULT_BPS, lookback: int = LOOKBACK) -> dict:
    rows = await conn.fetch("""
      SELECT i.id,i.candidate_id,i.hold_minutes,i.execution,o.raw_return_pct
      FROM canary_trade_intents i
      JOIN research_outcomes o ON o.candidate_id=i.candidate_id AND o.horizon_minutes=i.hold_minutes
      WHERE i.status='closed' AND i.execution IS NOT NULL
      ORDER BY i.updated_at DESC
      LIMIT $1
    """, int(lookback))
    samples=[]
    for row in rows:
        e=_obj(row['execution'])
        drag=implied_drag_bps(row['raw_return_pct'],e.get('strategy_horizon_pnl_sol'),e.get('entry_trade_sol'))
        if drag is None: continue
        samples.append({'intent_id':int(row['id']),'candidate_id':int(row['candidate_id']),
                        'hold_minutes':int(row['hold_minutes']),'drag_bps':drag})
    observed=statistics.median([x['drag_bps'] for x in samples]) if samples else None
    effective=float(baseline_bps)
    source='baseline'
    if len(samples) >= MIN_SAMPLES:
        effective=max(effective,float(observed));source='live_median_floor'
    return {'effective_bps':effective,'observed_median_bps':observed,'samples':samples,
            'sample_count':len(samples),'minimum_samples':MIN_SAMPLES,'source':source}

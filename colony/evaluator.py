"""Evaluate many ant genomes against one shared observation. No API calls here."""
from __future__ import annotations

def _num(obs, key, default=0.0):
    try: return float(obs.get(key, default) or default)
    except (TypeError, ValueError): return float(default)

def matches(genome: dict, obs: dict) -> bool:
    p, family = genome.get("parameters", {}), genome.get("family")
    if family == "reversal":
        return (_num(obs,"price_change_m5") <= _num(p,"price_change_m5_max",-8) and
                _num(obs,"dex_buy_ratio_m5") >= _num(p,"dex_buy_ratio_m5_min",.62))
    if family == "momentum":
        return (_num(obs,"price_change_m5") >= _num(p,"price_change_m5_min",5) and
                _num(obs,"volume_liquidity_m5") >= _num(p,"volume_liquidity_m5_min",.04))
    if family == "order_flow":
        return (_num(obs,"dex_buy_ratio_m5") >= _num(p,"dex_buy_ratio_m5_min",.8) and
                _num(obs,"buy_acceleration") >= _num(p,"buy_acceleration_min",1.5))
    if family == "wallet_convergence":
        return (_num(obs,"buy_wallets_30") >= _num(p,"buy_wallets_30_min",2) and
                _num(obs,"flow_ratio_15") >= _num(p,"flow_ratio_15_min",1.2))
    # Novel species use declarative predicates, so new families need no evaluator rewrite.
    return all(_predicate(_num(obs,k), rule) for k, rule in genome.get("predicates", {}).items())

def _predicate(value: float, rule) -> bool:
    if not isinstance(rule, dict): return False
    if "min" in rule and value < float(rule["min"]): return False
    if "max" in rule and value > float(rule["max"]): return False
    return True

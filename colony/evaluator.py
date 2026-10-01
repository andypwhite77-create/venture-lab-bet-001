"""Evaluate many ant genomes against one shared observation. No API calls here."""
from __future__ import annotations

def _num(obs, key, default=0.0):
    try: return float(obs.get(key, default) or default)
    except (TypeError, ValueError): return float(default)

def _observed_num(obs, key):
    if key not in obs or obs.get(key) is None: return None
    try: return float(obs.get(key))
    except (TypeError, ValueError): return None

def matches(genome: dict, obs: dict) -> bool:
    p, family = genome.get("parameters", {}), genome.get("family")
    if family == "reversal":
        pc=_observed_num(obs,"price_change_m5"); br=_observed_num(obs,"dex_buy_ratio_m5")
        return pc is not None and br is not None and pc <= _num(p,"price_change_m5_max",-8) and br >= _num(p,"dex_buy_ratio_m5_min",.62)
    if family == "momentum":
        pc=_observed_num(obs,"price_change_m5"); vl=_observed_num(obs,"volume_liquidity_m5")
        return pc is not None and vl is not None and pc >= _num(p,"price_change_m5_min",5) and vl >= _num(p,"volume_liquidity_m5_min",.04)
    if family == "order_flow":
        br=_observed_num(obs,"dex_buy_ratio_m5"); acc=_observed_num(obs,"buy_acceleration")
        return br is not None and acc is not None and br >= _num(p,"dex_buy_ratio_m5_min",.8) and acc >= _num(p,"buy_acceleration_min",1.5)
    if family == "wallet_convergence":
        bw=_observed_num(obs,"buy_wallets_30"); fr=_observed_num(obs,"flow_ratio_15")
        return bw is not None and fr is not None and bw >= _num(p,"buy_wallets_30_min",2) and fr >= _num(p,"flow_ratio_15_min",1.2)
    # Novel species use declarative predicates, so new families need no evaluator rewrite.
    # Missing sensor data is UNKNOWN, never zero. A predicate may only fire when
    # every sensor it depends on was actually observed for this candidate.
    for k, rule in genome.get("predicates", {}).items():
        if k not in obs or obs.get(k) is None:
            return False
        try:
            value=float(obs.get(k))
        except (TypeError, ValueError):
            return False
        if not _predicate(value, rule):
            return False
    return True

def _predicate(value: float, rule) -> bool:
    if not isinstance(rule, dict): return False
    if "min" in rule and value < float(rule["min"]): return False
    if "max" in rule and value > float(rule["max"]): return False
    return True

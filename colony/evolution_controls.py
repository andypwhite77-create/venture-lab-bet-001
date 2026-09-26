"""Deterministic experimental-control helpers. No live authority."""
from __future__ import annotations
import hashlib, random

def matched_random_control(genome_ids, n, seed):
    """Recorded-seed control selection that deliberately ignores fitness."""
    ids=sorted(set(genome_ids)); rng=random.Random(str(seed))
    if n>len(ids): raise ValueError('control sample exceeds founder population')
    return rng.sample(ids,n)

def epoch_fingerprint(parts: dict) -> str:
    """Stable provenance fingerprint for experimental semantics."""
    body='\n'.join(f'{k}={parts[k]}' for k in sorted(parts))
    return hashlib.sha256(body.encode()).hexdigest()

def absolute_viability(expectancy_after_friction, catastrophe_rate, min_expectancy=0.0, max_catastrophe=0.05):
    return float(expectancy_after_friction)>float(min_expectancy) and float(catastrophe_rate)<=float(max_catastrophe)

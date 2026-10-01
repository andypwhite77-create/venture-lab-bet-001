"""Map evolved hold genes to measured forward horizons without hindsight interpolation."""
from __future__ import annotations
MEASURED=(5,10,15,30,45,60,240,720,1440)

def measured_horizon(requested: int) -> int | None:
    requested=max(1,int(requested))
    return requested if requested in MEASURED else None

def outcome_for_hold(outcomes: dict[int,float], requested: int):
    h=measured_horizon(requested)
    return h,(outcomes.get(h) if h is not None else None)

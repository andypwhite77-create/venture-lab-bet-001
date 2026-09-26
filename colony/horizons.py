"""Map evolved hold genes to measured forward horizons without hindsight interpolation."""
from __future__ import annotations
MEASURED=(5,15,30,60,240,720,1440)

def measured_horizon(requested: int) -> int:
    requested=max(1,int(requested))
    # nearest measured horizon; ties choose shorter to reduce exposure assumption
    return min(MEASURED,key=lambda h:(abs(h-requested),h))

def outcome_for_hold(outcomes: dict[int,float], requested: int):
    h=measured_horizon(requested)
    return h,outcomes.get(h)

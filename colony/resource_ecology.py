"""Translate evidence-backed fitness into bounded ecological privileges."""
from colony.ecology import pressures

BASE_NOTIONAL=25.0
MAX_NOTIONAL=50.0
MIN_NOTIONAL=10.0

def allocation(rank_fraction,evidence_n,catastrophe_rate=0.0):
    p=pressures(rank_fraction,evidence_n,catastrophe_rate)
    confidence=p['evidence_weight']
    # Capital follows evidence slowly; rank alone cannot unlock the ceiling.
    upside=(MAX_NOTIONAL-BASE_NOTIONAL)*p['reproductive_access']
    downside=(BASE_NOTIONAL-MIN_NOTIONAL)*p['replacement_pressure']
    notional=max(MIN_NOTIONAL,min(MAX_NOTIONAL,BASE_NOTIONAL+upside-downside))
    offspring=max(0,min(3,round(3*p['reproductive_access'])))
    return {**p,'paper_notional':round(notional,2),'offspring_slots':offspring,
            'can_reproduce':offspring>0 and confidence>=1.0}

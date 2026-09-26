"""Ecological pressure model: competition without anthropomorphic 'want'."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Ecology:
    slots:int=100
    elite_share:float=.20
    replacement_share:float=.10
    exploration_share:float=.05

DEFAULT=Ecology()

def pressures(rank_fraction, evidence_n, catastrophe_rate=0.0):
    proven=min(1.0,evidence_n/30.0)
    survival=(1-rank_fraction)*proven
    reproduction=max(0.0,(DEFAULT.elite_share-rank_fraction)/DEFAULT.elite_share)*proven
    replacement=max(0.0,(rank_fraction-(1-DEFAULT.replacement_share))/DEFAULT.replacement_share)*proven
    if catastrophe_rate>0: replacement=max(replacement,min(1.0,catastrophe_rate*5))
    return {'survival_pressure':round(survival,4),'reproductive_access':round(reproduction,4),
            'replacement_pressure':round(replacement,4),'evidence_weight':round(proven,4)}

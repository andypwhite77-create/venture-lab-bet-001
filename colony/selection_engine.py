"""Shadow selection engine: recommends ecology outcomes; never mutates populations."""
from colony.resource_ecology import allocation
from colony.diversity import adjusted_reproductive_access,protected_family
from colony.regime_memory import stale_weight

def score_ant(ant,family_share):
    rank=float(ant['rank_fraction']); n=int(ant['evidence_n']); age=int(ant.get('age_windows',0))
    eco=allocation(rank,n,float(ant.get('catastrophe_rate',0)))
    access=adjusted_reproductive_access(eco['reproductive_access'],family_share)*stale_weight(age)
    niche=float(ant.get('specialist_bonus',0)); access=min(1.0,access+niche)
    return {**eco,'adjusted_reproductive_access':round(access,4),'rare_family_protected':protected_family(family_share)}

def shadow_plan(ants,family_shares,replacement_slots=10):
    scored=[]
    for ant in ants:
        x=score_ant(ant,family_shares.get(ant.get('family','unknown'),0)); scored.append({**ant,**x})
    breeders=sorted(scored,key=lambda x:x['adjusted_reproductive_access'],reverse=True)
    replaceable=[x for x in scored if not x['rare_family_protected']]
    replace=sorted(replaceable,key=lambda x:(x['replacement_pressure'],-x['rank_fraction']),reverse=True)[:replacement_slots]
    return {'mode':'shadow_only','breeders':[x['id'] for x in breeders if x['can_reproduce']][:20],
            'replace':[x['id'] for x in replace if x['replacement_pressure']>0], 'scored':scored}

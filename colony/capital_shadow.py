"""Shadow capital allocator. Models production promotion without live authority."""
import math
from collections import Counter

STARTER_GBP=25.0
INITIAL_SLOTS=25
GROWTH_SHARE=0.50
MAX_FAMILY_FRACTION=0.40
MIN_EVIDENCE=20
MIN_DISTINCT_FAMILIES=3
SURVIVAL_DOCTRINE='survival_through_variation'


def snapshot(selection, realised_net_sol, sol_gbp):
    ants=[dict(a) for a in selection.get('ants',[]) if int(a.get('n') or 0)>=MIN_EVIDENCE]
    ants.sort(key=lambda a: float(a.get('fitness') or -999), reverse=True)
    net_gbp=float(realised_net_sol or 0)*(float(sol_gbp) if sol_gbp is not None else 0.0)
    growth_reserve=max(0.0,net_gbp)*GROWTH_SHARE
    locked_profit=max(0.0,net_gbp)*(1.0-GROWTH_SHARE)
    earned_slots=int(growth_reserve//STARTER_GBP)
    target=min(len(ants),INITIAL_SLOTS+earned_slots)
    cap=max(1,math.ceil(target*MAX_FAMILY_FRACTION)) if target else 0
    chosen=[];counts=Counter(); chosen_ids=set()
    # Survival through variation: when multiple evidence-qualified families exist,
    # reserve the first seats across distinct families before filling by fitness.
    # Weak families are never forced in; only ants that already cleared MIN_EVIDENCE compete.
    by_family={}
    for a in ants:
        fam=a.get('family') or 'unknown'
        by_family.setdefault(fam,[]).append(a)
    family_heads=sorted((xs[0] for xs in by_family.values()), key=lambda a: float(a.get('fitness') or -999), reverse=True)
    diversity_target=min(MIN_DISTINCT_FAMILIES,len(family_heads),target)
    for a in family_heads[:diversity_target]:
        fam=a.get('family') or 'unknown'
        chosen.append(a);chosen_ids.add(a.get('genome_id'));counts[fam]+=1
    for a in ants:
        if len(chosen)>=target: break
        if a.get('genome_id') in chosen_ids: continue
        fam=a.get('family') or 'unknown'
        if counts[fam]>=cap: continue
        chosen.append(a);chosen_ids.add(a.get('genome_id'));counts[fam]+=1
    roster=[]
    for i,a in enumerate(chosen,1):
        roster.append({'rank':i,'genome_id':a.get('genome_id'),'family':a.get('family'),'fitness':a.get('fitness'),
                       'evidence_n':a.get('n'),'slot_source':'seed' if i<=INITIAL_SLOTS else 'earned'})
    total=max(1,len(chosen)); shares=[n/total for n in counts.values()]
    hhi=sum(x*x for x in shares) if chosen else 1.0
    largest=max(shares,default=1.0)
    distinct=len(counts)
    return {'mode':'shadow_only','live_authority':False,'starter_gbp':STARTER_GBP,'initial_slots':INITIAL_SLOTS,
            'growth_share':GROWTH_SHARE,'max_family_fraction':MAX_FAMILY_FRACTION,'min_evidence':MIN_EVIDENCE,
            'survival_doctrine':SURVIVAL_DOCTRINE,'min_distinct_families_when_available':MIN_DISTINCT_FAMILIES,
            'realised_net_gbp':net_gbp,'growth_reserve_gbp':growth_reserve,'locked_profit_gbp':locked_profit,
            'earned_slots':earned_slots,'active_slots':len(roster),'target_slots':target,
            'eligible_pool':len(ants),'family_counts':dict(counts),'distinct_families':distinct,
            'largest_family_fraction':largest,'concentration_hhi':hhi,
            'monoculture_risk':'high' if largest>.60 else ('medium' if largest>.40 or distinct<2 else 'low'),
            'roster':roster}

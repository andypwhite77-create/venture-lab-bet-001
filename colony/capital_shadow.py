"""Shadow capital allocator. Models production promotion without live authority."""
import math
from collections import Counter

STARTER_GBP=25.0
INITIAL_SLOTS=25
GROWTH_SHARE=0.50
MAX_FAMILY_FRACTION=0.40
MIN_EVIDENCE=20


def snapshot(selection, realised_net_sol, sol_gbp):
    ants=[dict(a) for a in selection.get('ants',[]) if int(a.get('n') or 0)>=MIN_EVIDENCE]
    ants.sort(key=lambda a: float(a.get('fitness') or -999), reverse=True)
    net_gbp=float(realised_net_sol or 0)*(float(sol_gbp) if sol_gbp is not None else 0.0)
    growth_reserve=max(0.0,net_gbp)*GROWTH_SHARE
    locked_profit=max(0.0,net_gbp)*(1.0-GROWTH_SHARE)
    earned_slots=int(growth_reserve//STARTER_GBP)
    target=min(len(ants),INITIAL_SLOTS+earned_slots)
    cap=max(1,math.ceil(target*MAX_FAMILY_FRACTION)) if target else 0
    chosen=[];counts=Counter()
    for a in ants:
        fam=a.get('family') or 'unknown'
        if counts[fam]>=cap: continue
        chosen.append(a);counts[fam]+=1
        if len(chosen)>=target: break
    roster=[]
    for i,a in enumerate(chosen,1):
        roster.append({'rank':i,'genome_id':a.get('genome_id'),'family':a.get('family'),'fitness':a.get('fitness'),
                       'evidence_n':a.get('n'),'slot_source':'seed' if i<=INITIAL_SLOTS else 'earned'})
    return {'mode':'shadow_only','live_authority':False,'starter_gbp':STARTER_GBP,'initial_slots':INITIAL_SLOTS,
            'growth_share':GROWTH_SHARE,'max_family_fraction':MAX_FAMILY_FRACTION,'min_evidence':MIN_EVIDENCE,
            'realised_net_gbp':net_gbp,'growth_reserve_gbp':growth_reserve,'locked_profit_gbp':locked_profit,
            'earned_slots':earned_slots,'active_slots':len(roster),'target_slots':target,
            'eligible_pool':len(ants),'family_counts':dict(counts),'roster':roster}

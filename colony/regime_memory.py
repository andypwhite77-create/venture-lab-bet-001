"""Remember environmental regimes without letting old regimes dominate forever."""
from collections import defaultdict

def summarize(observations,min_n=5):
    groups=defaultdict(list)
    for o in observations:
        for niche in o.get('niches',['generalist']): groups[niche].append(float(o['return_pct']))
    return {k:{'n':len(v),'mean':round(sum(v)/len(v),4),'positive_rate':round(sum(x>0 for x in v)/len(v),4)}
            for k,v in groups.items() if len(v)>=min_n}

def drift(previous,current,min_shift=5.0):
    events=[]
    for k,now in current.items():
        old=previous.get(k)
        if not old: continue
        shift=now['mean']-old['mean']
        if abs(shift)>=min_shift: events.append({'niche':k,'mean_shift_pct':round(shift,4),'direction':'improved' if shift>0 else 'degraded'})
    return events

def stale_weight(age_windows,half_life=4):
    return round(.5**(age_windows/half_life),4)

"""Propose candidate niches from sensory features; adoption happens elsewhere."""
from itertools import combinations

def binary_features(row):
    out={}
    for k,v in row.items():
        if isinstance(v,bool): out[k]=v
        elif isinstance(v,(int,float)) and v is not None:
            out[k+'__high']=v>0
    return out

def discover(rows,min_n=12,min_effect=5.0):
    if len(rows)<min_n:return []
    keys=sorted(k for k in set().union(*(binary_features(r).keys() for r in rows)) if not k.startswith('return_pct'))
    proposals=[]
    for a,b in combinations(keys,2):
        yes=[r['return_pct'] for r in rows if binary_features(r).get(a) and binary_features(r).get(b)]
        no=[r['return_pct'] for r in rows if not (binary_features(r).get(a) and binary_features(r).get(b))]
        if len(yes)<min_n or len(no)<min_n:continue
        effect=sum(yes)/len(yes)-sum(no)/len(no)
        if abs(effect)>=min_effect: proposals.append({'features':[a,b],'n':len(yes),'effect_pct':round(effect,4),'status':'candidate_only'})
    return sorted(proposals,key=lambda x:abs(x['effect_pct']),reverse=True)

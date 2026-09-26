"""Selection engine: unique-entity evidence, tail penalties, diversity preservation."""
from __future__ import annotations
import math, statistics
from colony.fitness import score as fitness_score
from colony.genome import genome_id, mutate

def ant_metrics(returns: list[tuple[str,float]]) -> dict:
    # One result per independent entity: repeated signals cannot inflate confidence.
    first={}
    for entity, ret in returns: first.setdefault(entity,float(ret))
    vals=list(first.values()); n=len(vals)
    if not vals: return {"n":0,"fitness":-999.0}
    avg=statistics.fmean(vals); med=statistics.median(vals)
    downside=[x for x in vals if x<0]
    catastrophe=sum(x <= -25 for x in vals)/n
    consistency=1.0-(statistics.pstdev(vals)/max(10.0,abs(avg))) if n>1 else 0.0
    robustness=min(avg,med)/100.0
    m={"n":n,"expectancy":avg/100.0,"consistency":max(-2,min(1,consistency)),
       "robustness":robustness,"max_drawdown":abs(min(0,min(vals)))/100.0,
       "catastrophe_rate":catastrophe,"novelty":0.0,"resource_cost":0.0}
    m["fitness"]=fitness_score(m); m["avg_return_pct"]=avg; m["median_return_pct"]=med
    return m

def select(population: list[dict], metrics: dict[str,dict], survivors=20, max_family_fraction=.40) -> list[dict]:
    ranked=sorted(population,key=lambda g:metrics.get(genome_id(g),{}).get("fitness",-999),reverse=True)
    chosen=[]; counts={}; cap=max(1,math.ceil(survivors*max_family_fraction))
    for g in ranked:
        fam=g["family"]
        if counts.get(fam,0)>=cap: continue
        chosen.append(g); counts[fam]=counts.get(fam,0)+1
        if len(chosen)>=survivors: break
    return chosen

def reproduce(survivors: list[dict], target=100, seed=1, exploration_fraction=.20) -> list[dict]:
    import random
    rng=random.Random(seed); out=list(survivors); seen={genome_id(g) for g in out}
    attempts=0
    while len(out)<target and attempts<target*100:
        attempts+=1; parent=rng.choice(survivors)
        child=mutate(parent,seed=rng.randrange(2**31))
        gid=genome_id(child)
        if gid not in seen: out.append(child); seen.add(gid)
    return out[:target]

def classify(m: dict) -> str:
    if m.get("n",0)<8: return "unknown"
    f=m.get("fitness",-999)
    if f<0: return "stressed"
    if f<.15: return "viable"
    if f<.35: return "thriving"
    return "reproductive"

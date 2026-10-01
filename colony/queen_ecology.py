"""Queen expertise: journal, niches, aging, opportunity map and shadow comparison.
Breeding-visible evidence only; Spartan/holdout details never enter this module.
"""
import json,os,time,math,collections
PATH="/data/queen_ecology.json"

def load():
    try: return json.load(open(PATH))
    except Exception: return {"journal":[],"graveyard":{},"niches":{},"opportunity_map":{},"beliefs":{},"shadow":{}}

def save(x):
    os.makedirs(os.path.dirname(PATH),exist_ok=True);t=PATH+".tmp";json.dump(x,open(t,"w"),indent=2);os.replace(t,PATH)

def signature(g):
    p=g.get("predicates",{}); hold=g.get("parameters",{}).get("hold_minutes")
    return f"h{hold}:"+",".join(sorted(p))

def learn(finalists,summary,campaign):
    e=load(); now=time.time(); groups=collections.defaultdict(list)
    for x in finalists: groups[signature(x.get("genome",{}))].append(x)
    for sig,xs in groups.items():
        scores=[float(x.get("selection_score",0)) for x in xs]; n=e["niches"].setdefault(sig,{"campaigns":0,"seen":0,"score_ema":0.0,"last_seen":0})
        n["campaigns"]+=1;n["seen"]+=len(xs);n["score_ema"]=.7*n["score_ema"]+.3*(sum(scores)/len(scores));n["last_seen"]=now
    # Knowledge aging: unsupported beliefs decay each campaign.
    for b in e["beliefs"].values(): b["confidence"]*=.92
    for sig,xs in groups.items():
        b=e["beliefs"].setdefault(sig,{"confidence":0.0,"evidence":0});b["confidence"]=min(1,.92*b["confidence"]+.12);b["evidence"]+=len(xs)
    e["journal"].append({"campaign":campaign,"at":now,"tested":summary.get("tested"),"finalists":len(finalists),"niches":len(groups)})
    e["journal"]=e["journal"][-100:]
    # Graveyard is fed by explicitly failed breeding-visible niches, not just finalists.
    failures=e.setdefault('failures',{})
    for item in summary.get('weak_niches',[]):
        sig=item.get('signature'); cnt=int(item.get('count',0) or 0)
        if not sig: continue
        z=failures.setdefault(sig,{'campaigns':0,'count':0,'last_seen':0})
        z['campaigns']+=1; z['count']+=cnt; z['last_seen']=now
        if z['campaigns']>=2 and z['count']>=20:
            e['graveyard'][sig]={"reason":"repeated breeding-visible failure","at":now,"revisitable":True,"campaigns":z['campaigns'],"count":z['count']}
    e["opportunity_map"]={"underexplored_sensors":summary.get("underexplored_sensors",[]),"updated":now}
    save(e);return e

def strategy(e):
    active=sorted(((v.get("confidence",0),k) for k,v in e.get("beliefs",{}).items()),reverse=True)[:8]
    return {"exploit":.55,"adjacent_explore":.25,"wild_scouts":.20,"top_niches":[k for _,k in active],"graveyard_size":len(e.get("graveyard",{}))}

"""Persistent research-only credit for Queen mutation operators.
Uses breeding-visible parent->child score deltas only; never Spartan/holdout answers.
"""
from __future__ import annotations
import json, math, os, time

PATH='/data/queen_mutation_credit.json'
OPERATORS=('local','standard','wide')
FLOOR=0.10
RECENT_BLEND=0.65

def _blank():
    return {'version':1,'updated_at':None,'operators':{
        k:{'trials':0,'wins':0,'delta_sum':0.0,'recent':[]} for k in OPERATORS}}

def load():
    state=_blank()
    if os.path.exists(PATH):
        try:
            with open(PATH) as f: saved=json.load(f)
            if saved.get('version')==1: state.update(saved)
        except Exception: pass
    for k in OPERATORS:
        state.setdefault('operators',{}).setdefault(k,_blank()['operators'][k])
    return state

def save(state):
    os.makedirs(os.path.dirname(PATH),exist_ok=True)
    state['updated_at']=time.time()
    tmp=PATH+'.tmp'
    with open(tmp,'w') as f: json.dump(state,f,indent=2)
    os.replace(tmp,PATH)

def _quality(win_rate,mean_delta):
    return max(0.05,0.70*float(win_rate)+0.30*(0.5+0.5*math.tanh(float(mean_delta)*4)))

def weights(state=None):
    state=state or load(); raw={}
    for k in OPERATORS:
        z=state['operators'][k]; n=max(0,int(z.get('trials',0)))
        wins=max(0,int(z.get('wins',0))); mean=float(z.get('delta_sum',0.0))/max(1,n)
        lifetime=_quality((wins+2.0)/(n+4.0),mean)
        recent=list(z.get('recent',[]))[-200:]
        if recent:
            rn=len(recent); rw=sum(1 for x in recent if x.get('win'))
            rd=sum(float(x.get('delta',0.0)) for x in recent)/rn
            recent_quality=_quality((rw+2.0)/(rn+4.0),rd)
            raw[k]=(1.0-RECENT_BLEND)*lifetime+RECENT_BLEND*recent_quality
        else:
            raw[k]=lifetime
    total=sum(raw.values()) or 1.0
    norm={k:raw[k]/total for k in OPERATORS}
    free=max(0.0,1.0-FLOOR*len(OPERATORS))
    return {k:FLOOR+free*norm[k] for k in OPERATORS}

def choose(rng,state=None):
    w=weights(state); x=rng.random(); acc=0.0
    for k in OPERATORS:
        acc+=w[k]
        if x<=acc:return k
    return OPERATORS[-1]

def record(operator,parent_score,child_score,state=None):
    if operator not in OPERATORS:return state or load()
    state=state or load(); z=state['operators'][operator]
    p=float(parent_score); c=float(child_score)
    delta=-1.0 if c<=-900 else max(-1.0,min(1.0,c-p))
    z['trials']=int(z.get('trials',0))+1
    z['wins']=int(z.get('wins',0))+int(c>p and c>-900)
    z['delta_sum']=float(z.get('delta_sum',0.0))+delta
    recent=list(z.get('recent',[])); recent.append({'at':time.time(),'delta':delta,'win':bool(c>p and c>-900)})
    z['recent']=recent[-200:]
    return state

def summarise(state=None):
    state=state or load(); w=weights(state); out={}
    for k in OPERATORS:
        z=state['operators'][k]; n=int(z.get('trials',0)); wins=int(z.get('wins',0))
        out[k]={'trials':n,'wins':wins,'win_rate':wins/max(1,n),
                'mean_delta':float(z.get('delta_sum',0.0))/max(1,n),'weight':w[k]}
    return out

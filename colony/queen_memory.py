"""Persistent Queen research memory. Contains only breeding-visible evidence."""
import json,os,collections,math
from colony.queen_experience import load_experience
PATH='/data/queen_memory.json'

def load_memory():
    base={'campaigns':0,'feature_stats':{},'species':{},'lessons':[]}
    if os.path.exists(PATH):
        try: base.update(json.load(open(PATH)))
        except Exception: pass
    exp=load_experience()
    base['prospective_preferred_features']=exp.get('preferred_features',[])
    base['prospective_parent_templates']=exp.get('parent_templates',[])
    base['prospective_experience_mints']=exp.get('experienced_mints',[])
    base['prospective_experience_summary']={k:exp.get(k) for k in ('updated_at','observations','career_count','eligible_careers')}
    return base

def save_memory(m):
    os.makedirs(os.path.dirname(PATH),exist_ok=True)
    tmp=PATH+'.tmp';json.dump(m,open(tmp,'w'),indent=2);os.replace(tmp,PATH)

def learn_campaign(finalists,summary):
    m=load_memory();m['campaigns']=m.get('campaigns',0)+1
    fs=m.setdefault('feature_stats',{})
    for x in finalists:
        score=float(x.get('selection_score',0)); g=x.get('genome',{})
        for k in g.get('predicates',{}):
            z=fs.setdefault(k,{'seen':0,'score_sum':0.0,'positive':0})
            z['seen']+=1;z['score_sum']+=score;z['positive']+=int(score>0);z['last_campaign']=m['campaigns']
    ranked=sorted(fs.items(),key=lambda kv:(kv[1]['score_sum']/max(1,kv[1]['seen']),kv[1]['seen']),reverse=True)
    # Age stale expertise and expose underexplored territory.
    for z in fs.values(): z['score_sum']*=.96
    m['preferred_features']=[k for k,_ in ranked[:6]]
    m['underexplored_features']=[k for k,z in sorted(fs.items(),key=lambda kv:kv[1]['seen'])[:5]]
    m['lessons']=(m.get('lessons',[])+[{'campaign':m['campaigns'],'tested':summary.get('tested'),'finalists':summary.get('finalists'),'holdout_withheld':True,'preferred_features':m['preferred_features']}])[-30:]
    save_memory(m);return m

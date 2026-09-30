"""Persistent Queen research memory. Contains only breeding-visible evidence."""
import json,os,collections,math
PATH='/data/queen_memory.json'

def load_memory():
    if not os.path.exists(PATH): return {'campaigns':0,'feature_stats':{},'species':{},'lessons':[]}
    try: return json.load(open(PATH))
    except Exception: return {'campaigns':0,'feature_stats':{},'species':{},'lessons':[]}

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
            z['seen']+=1;z['score_sum']+=score;z['positive']+=int(score>0)
    ranked=sorted(fs.items(),key=lambda kv:(kv[1]['score_sum']/max(1,kv[1]['seen']),kv[1]['seen']),reverse=True)
    m['preferred_features']=[k for k,_ in ranked[:6]]
    m['lessons']=(m.get('lessons',[])+[{'campaign':m['campaigns'],'tested':summary.get('tested'),'finalists':summary.get('finalists'),'holdout_withheld':True,'preferred_features':m['preferred_features']}])[-30:]
    save_memory(m);return m

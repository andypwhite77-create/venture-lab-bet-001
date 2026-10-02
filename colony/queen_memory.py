"""Persistent Queen research memory. Genetics learn from breeding-visible and quarantined prospective evidence; Spartan contributes only aggregate pass/drought counts, never thresholds or holdout answers."""
import json,os,collections,math,logging,statistics,time
from colony.queen_experience import load_experience
PATH='/data/queen_memory.json'

def load_memory():
    base={'campaigns':0,'feature_stats':{},'species':{},'lessons':[]}
    if os.path.exists(PATH):
        try:
            with open(PATH) as f: base.update(json.load(f))
        except Exception:
            logging.exception('queen_memory_load_failed path=%s',PATH)
    exp=load_experience()
    base['prospective_preferred_features']=exp.get('preferred_features',[])
    base['prospective_parent_templates']=exp.get('parent_templates',[])
    base['prospective_experience_mints']=exp.get('experienced_mints',[])
    base['prospective_experience_summary']={k:exp.get(k) for k in ('updated_at','observations','career_count','eligible_careers')}
    return base

def save_memory(m):
    os.makedirs(os.path.dirname(PATH),exist_ok=True)
    tmp=PATH+'.tmp'
    with open(tmp,'w') as f: json.dump(m,f,indent=2)
    os.replace(tmp,PATH)

def _campaign_quality(finalists,summary):
    if not finalists:
        return {'at':time.time(),'tested':summary.get('tested',0),'finalists':0,'behaviour_groups':0}
    def med(key,part):
        vals=[float(x.get(part,{}).get(key,0) or 0) for x in finalists]
        return statistics.median(vals) if vals else 0.0
    behaviours=set(); predicates=[]; scores=[]; concentrations=[]
    for x in finalists:
        g=x.get('genome',{}); prm=g.get('parameters',{})
        behaviours.add((x.get('train',{}).get('event_signature'),x.get('validation',{}).get('event_signature'),prm.get('hold_minutes'),prm.get('stop_loss_pct'),prm.get('take_profit_pct')))
        predicates.append(len(g.get('predicates',{})));scores.append(float(x.get('selection_score',-999) or -999))
        concentrations.append(max(float(x.get('train',{}).get('outlier',1) or 1),float(x.get('validation',{}).get('outlier',1) or 1)))
    return {'at':time.time(),'tested':summary.get('tested',0),'finalists':len(finalists),'behaviour_groups':len(behaviours),
            'median_train_n':med('n','train'),'median_validation_n':med('n','validation'),
            'median_concentration':statistics.median(concentrations),'median_predicates':statistics.median(predicates),
            'median_selection_score':statistics.median(scores),'methodology_version':summary.get('methodology_version')}


def record_exam_result(result):
    m=load_memory(); hist=m.setdefault('exam_history',[])
    completed=result.get('completed_at')
    if completed is not None and any(x.get('completed_at')==completed for x in hist):
        return m
    hist.append({'at':time.time(),'completed_at':completed,'campaign':result.get('campaign'),'tested':result.get('tested'),'finalists':result.get('finalists'),
                 'spartan_survivors':result.get('spartan_survivors',0),'distinct_survivor_behaviours':result.get('distinct_survivor_behaviours',0)})
    m['exam_history']=hist[-30:]
    drought=0
    for x in reversed(m['exam_history']):
        if int(x.get('spartan_survivors',0) or 0)>0:break
        drought+=1
    m['spartan_drought_campaigns']=drought
    save_memory(m);return m


def learn_campaign(finalists,summary):
    m=load_memory();m['campaigns']=m.get('campaigns',0)+1
    exp=load_experience(); exp_stats=exp.get('feature_stats',{}) or {}
    fs=m.setdefault('feature_stats',{})
    for x in finalists:
        score=float(x.get('selection_score',0)); g=x.get('genome',{})
        tn=float(x.get('train',{}).get('n',0) or 0); vn=float(x.get('validation',{}).get('n',0) or 0)
        conc=max(float(x.get('train',{}).get('outlier',1) or 1),float(x.get('validation',{}).get('outlier',1) or 1))
        predicates=len(g.get('predicates',{}))
        quality=score + .008*min(tn,140) + .014*min(vn,70) - .40*max(0,conc-.30) - .04*max(0,predicates-2)
        for k in g.get('predicates',{}):
            z=fs.setdefault(k,{'seen':0,'score_sum':0.0,'quality_sum':0.0,'breadth_sum':0.0,'positive':0})
            z['seen']+=1;z['score_sum']+=score;z['quality_sum']=z.get('quality_sum',0.0)+quality
            z['breadth_sum']=z.get('breadth_sum',0.0)+min(tn,140)+min(vn,70);z['positive']+=int(score>0);z['last_campaign']=m['campaigns']
    # Rank historical-safe learning together with genuinely prospective career evidence.
    def rank_value(item):
        k,z=item; n=max(1,z.get('seen',0)); hist=z.get('quality_sum',z.get('score_sum',0.0))/n
        ez=exp_stats.get(k,{}) or {}; en=max(1,int(ez.get('ants',0) or 0)); prospective=float(ez.get('weighted_score',0) or 0)/en
        return (hist + .35*prospective, z.get('seen',0)+int(ez.get('events',0) or 0))
    ranked=sorted(fs.items(),key=rank_value,reverse=True)
    for z in fs.values():
        z['score_sum']*=.96; z['quality_sum']=z.get('quality_sum',0.0)*.96
    m['preferred_features']=[k for k,_ in ranked[:8]]
    m['underexplored_features']=[k for k,z in sorted(fs.items(),key=lambda kv:kv[1]['seen'])[:6]]
    q=_campaign_quality(finalists,summary);qh=m.setdefault('quality_history',[]);qh.append(q);m['quality_history']=qh[-30:]
    m['lessons']=(m.get('lessons',[])+[{'campaign':m['campaigns'],'tested':summary.get('tested'),'finalists':summary.get('finalists'),
        'holdout_withheld':True,'preferred_features':m['preferred_features'],'quality':q,
        'prospective_parent_templates':len(exp.get('parent_templates',[]) or [])}])[-30:]
    save_memory(m);return m

"""Advisory Queen research grading. Historical success is never trading authority."""
def grade(result):
 if result.get('status')!='historical_discovery_only':return {'status':'inconclusive','credit':0}
 train=result.get('training',{});later=result.get('chronological_mint_holdout',{})
 def delta(v):
  a=v.get('selected_mean_pct');b=v.get('other_mean_pct')
  return None if a is None or b is None else round(float(a)-float(b),4)
 a=delta(train);b=delta(later)
 if a is None or b is None or min(later.get('selected_n',0),later.get('other_n',0))<10:status='insufficient_evidence'
 elif a>0 and b>0:status='historically_consistent'
 elif a>0:status='historically_refuted'
 else:status='no_training_advantage'
 return {'status':status,'credit':int(status=='historically_consistent'),'training_delta_pp':a,'later_delta_pp':b,'economic_reward':None,'promotion_allowed':False}

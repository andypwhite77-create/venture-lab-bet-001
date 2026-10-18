import json
from colony.queen_research_incentives import grade

def summarize(rows):
 experiments={};queens={}
 for r in rows:
  key=(r['feature'],r['direction'])
  result=r['result']
  if isinstance(result,str):result=json.loads(result)
  status=grade(result)
  x=experiments.setdefault(key,{'feature':key[0],'direction':key[1],'attempts':0})
  x['attempts']+=1
  q=queens.setdefault(r['queen'],{'attempts':0,'historical_flags':0})
  q['attempts']+=1;q['historical_flags']+=status['credit']
 return {'experiments':list(experiments.values()),'queens':queens,'authority':'advisory_only','holdout_reused':True}

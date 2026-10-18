"""Read-only entry-feature diagnostics with chronological holdout.
Exploratory association, NOT a predictive model, fills, or promotion evidence.
"""
import asyncio,json,math,statistics
from db import init_db,connection
from colony.prospective_exit_trial import TRIAL
FIELDS=('liquidity_usd','volume_m5','price_change_m5','price_change_h1','dex_buy_ratio_m5','volume_liquidity_m5','buy_acceleration')

def _obj(value):
 return json.loads(value) if isinstance(value,str) else dict(value or {})
def _num(value):
 try:
  n=float(value)
  return n if math.isfinite(n) else None
 except (ValueError,TypeError):return None

def evaluate(rows):
 items=[];excluded=0
 for row in sorted(rows,key=lambda r:(r['entry_at'],r['candidate_id'])):
  outcome=_obj(row['outcome']);rec=outcome.get('stop_10_take_15')
  if not isinstance(rec,dict) or rec.get('status')!='observed_path':excluded+=1;continue
  y=_num(rec.get('net_pct'))
  if y is None:excluded+=1;continue
  features=_obj(row['features']);items.append({'id':row['candidate_id'],'y':y,'features':features})
 cut=max(1,int(len(items)*.7)) if len(items)>1 else len(items)
 train,test=items[:cut],items[cut:]
 diagnostics={}
 for name in FIELDS:
  known=[(v,i['y']) for i in train if (v:=_num(i['features'].get(name))) is not None]
  if len(known)<8:diagnostics[name]={'status':'insufficient_training_feature_coverage','training_feature_count':len(known)};continue
  threshold=statistics.median(v for v,_ in known)
  def split(data):
   pairs=[(_num(i['features'].get(name)),i['y']) for i in data]
   pairs=[(v,y) for v,y in pairs if v is not None]
   low=[y for v,y in pairs if v<=threshold];high=[y for v,y in pairs if v>threshold]
   return {'covered':len(pairs),'low_n':len(low),'high_n':len(high),'low_mean_pct':round(statistics.mean(low),4) if low else None,'high_mean_pct':round(statistics.mean(high),4) if high else None}
  diagnostics[name]={'status':'descriptive_only','train_median_threshold':threshold,'train':split(train),'chronological_holdout':split(test)}
 return {'matched_outcomes':len(items),'excluded':excluded,'training_n':len(train),'holdout_n':len(test),'features':diagnostics,'authority':'exploratory_entry_associations_no_trading','limitations':'one small non-independent candidate stream; thresholds discovered on training only; holdout is a diagnostic not proof; no causal or executable claim'}
async def run():
 await init_db()
 async with connection() as c:
  rows=await c.fetch('''SELECT t.candidate_id,t.entry_at,t.outcome,r.features FROM prospective_exit_trial_results t JOIN research_candidates r ON r.id=t.candidate_id WHERE t.trial=$1 ORDER BY t.entry_at,t.candidate_id''',TRIAL)
 return evaluate(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

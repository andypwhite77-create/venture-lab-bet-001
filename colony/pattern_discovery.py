"""Profit-pattern discovery over stored features using walk-forward rule mining.
Discovery only. Rules require chronological validation and create no execution authority.
"""
from __future__ import annotations
import itertools, json, math, statistics
from colony.historical_nursery import load_rows, split_rows, score

FEATURES=('price_change_m5','price_change_h1','volume_liquidity_m5','dex_buy_ratio_m5','buy_acceleration','buy_wallets_30','flow_ratio_15','buys_15','sells_15','buys_30','sells_30','liquidity_usd','volume_m5')

def quantiles(vals):
 vals=sorted(v for v in vals if math.isfinite(v)); n=len(vals)
 if n<20:return []
 return sorted(set(vals[min(n-1,int((n-1)*q))] for q in (.15,.25,.40,.60,.75,.85)))

def build_rules(rows):
 qs={f:quantiles([float(r['flat'].get(f,0) or 0) for r in rows]) for f in FEATURES}
 singles=[]
 for f,vs in qs.items():
  for v in vs:singles.extend([((f,'min',v),),((f,'max',v),)])
 # Focus pair search on flow/price/activity features to avoid combinatorial explosion.
 core=[r for r in singles if r[0][0] in ('dex_buy_ratio_m5','buy_acceleration','buy_wallets_30','flow_ratio_15','price_change_m5','volume_liquidity_m5')]
 pairs=[]
 for a,b in itertools.combinations(core,2):
  if a[0][0]!=b[0][0]:pairs.append((a[0],b[0]))
 return singles+pairs

def match(rule,row):
 for f,op,v in rule:
  try:x=float(row['flat'].get(f,0) or 0)
  except:return False
  if op=='min' and x<v:return False
  if op=='max' and x>v:return False
 return True

def eval_rule(rule,rows,horizon=15):
 first={}
 for r in rows:
  if match(rule,r) and r['returns']:
   h=horizon if horizon in r['returns'] else min(r['returns'],key=lambda x:abs(x-horizon))
   first.setdefault(r['mint'],float(r['returns'][h]))
 return score(list(first.items()))

async def discover(conn,limit=30):
 rows=await load_rows(conn); train,val,hold=split_rows(rows); rules=build_rules(train); found=[]
 horizons=(5,15,30,60,240)
 for rule in rules:
  for horizon in horizons:
   a,b,c=(eval_rule(rule,s,horizon) for s in (train,val,hold))
   if min(a['n'],b['n'],c['n'])<4:continue
   robust=.2*a['nursery_score']+.35*b['nursery_score']+.45*c['nursery_score']+.4*min(a['nursery_score'],b['nursery_score'],c['nursery_score'])
   found.append({'rule':rule,'horizon_minutes':horizon,'train':a,'validation':b,'holdout':c,'robust_score':robust})
 found.sort(key=lambda x:x['robust_score'],reverse=True)
 positive=sum(x['robust_score']>0 for x in found)
 return {'tested_rules':len(rules)*len(horizons),'qualified':len(found),'positive_robust':positive,'top':found[:limit]}

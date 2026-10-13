"""Read-only historian quality/regime audit. Never grants qualification authority."""
import asyncio,json,statistics
from collections import defaultdict
from datetime import timedelta,datetime,timezone
from db import init_db,connection

def classify(prices):
 if len(prices)<8:return 'insufficient'
 first,last=prices[0],prices[-1]
 if first<=0:return 'invalid'
 changes=[(b/a-1)*100 for a,b in zip(prices,prices[1:]) if a>0]
 if len(changes)<7:return 'insufficient'
 trend=(last/first-1)*100
 vol=statistics.pstdev(changes)
 if vol>=5:return 'high_volatility'
 if trend>=3:return 'rising'
 if trend<=-3:return 'falling'
 return 'sideways'

def coverage(samples,start,end,step_seconds=60,max_gap_seconds=180):
 points=sorted(t for t in samples if start<=t<=end)
 expected=max(1,int((end-start).total_seconds()//step_seconds)+1)
 if not points:return {'observed':0,'expected':expected,'complete':False,'largest_gap_seconds':None}
 gaps=[(points[0]-start).total_seconds(),(end-points[-1]).total_seconds()]
 gaps.extend((b-a).total_seconds() for a,b in zip(points,points[1:]))
 return {'observed':len(points),'expected':expected,
   'complete':max(gaps)<=max_gap_seconds and len(points)>=max(2,int(expected*.70)),
   'largest_gap_seconds':round(max(gaps),1)}

def disagreement(rows,max_age_seconds=120):
 # Only truly independent provider readings near in time count as a cross-check.
 groups=defaultdict(list)
 for r in rows:groups[r['provider']].append(r)
 pairs=[]
 for a,items in groups.items():
  for b,other in groups.items():
   if a>=b:continue
   for x in items:
    neighbors=[y for y in other if abs((x['collected_at']-y['collected_at']).total_seconds())<=max_age_seconds]
    if not neighbors:continue
    y=min(neighbors,key=lambda z:abs((x['collected_at']-z['collected_at']).total_seconds()))
    pairs.append(abs(x['price']-y['price'])/min(x['price'],y['price'])*100)
 return {'pairs':len(pairs),'max_disagreement_pct':round(max(pairs),3) if pairs else None,
  'warning':'unverified_single_provider' if not pairs else ('provider_disagreement' if max(pairs)>2 else 'no_large_disagreement_observed')}

async def run(limit=120):
 await init_db()
 async with connection() as c:
  mints=await c.fetch('SELECT mint,max(collected_at) newest FROM market_price_history GROUP BY mint ORDER BY newest DESC LIMIT $1',limit)
  output=[]
  for m in mints:
   newest=datetime.now(timezone.utc);start=newest-timedelta(minutes=30)
   rows=await c.fetch("""SELECT collected_at,price,provider FROM market_price_history
    WHERE mint=$1 AND collected_at BETWEEN $2 AND $3 ORDER BY collected_at""",m['mint'],start,newest)
   points=[dict(x) for x in rows]
   quality=coverage([p['collected_at'] for p in points],start,newest)
   comparison=disagreement(points)
   output.append({'mint':m['mint'],'coverage':quality,'regime':classify([p['price'] for p in points]) if quality['complete'] else 'unclassified_incomplete',
      'providers':sorted({p['provider'] for p in points}),'agreement':comparison})
 return {'mints':len(output),'complete_30m':sum(x['coverage']['complete'] for x in output),
  'regime_counts':{k:sum(x['regime']==k for x in output) for k in sorted({x['regime'] for x in output})},
  'independent_provider_crosschecks':sum(x['agreement']['pairs'] for x in output),
  'warnings':['Provider differences compare nearby receipt times, not synchronized source-side quote timestamps.', 'Regime labels are crude descriptive heuristics and cannot be used for trading or qualification.'],
  'sample':output[:8],'authority':'observational_only_no_training_no_spartan_no_live'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

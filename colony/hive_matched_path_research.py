"""Read-only matched observed price-path and feature diagnostic; no qualifications."""
import asyncio,json,statistics
from datetime import timedelta
from db import init_db,connection
from colony.hive_exit_path_audit import simulate

RUN='reversal-novelty-study-v1'
def matched_edges(rows):
 controls={r['candidate_id']:r for r in rows if r['species']=='observation_control' and r['status']=='observed_path'}
 result={}
 for species in {r['species'] for r in rows if r['species']!='observation_control'}:
  paired={r['candidate_id']:r for r in rows if r['species']==species and r['status']=='observed_path' and r['candidate_id'] in controls}
  edges=[r['net_pct']-controls[cid]['net_pct'] for cid,r in paired.items()]
  result[species]={'matched_distinct_opportunities':len(paired),'mean_paper_edge_pct_points':round(statistics.fmean(edges),4) if edges else None,'status':'exploratory_only' if len(paired)>=30 else 'insufficient'}
 return result

def summarize(rows,min_opportunities=30):
 groups={}
 for r in rows:
  groups.setdefault(r['species'],[]).append(r)
 output={}
 for name,items in groups.items():
  valid=[r for r in items if r['status']=='observed_path']
  uniq={r['candidate_id']:r for r in valid}
  gains=[r['net_pct'] for r in uniq.values()]
  output[name]={'entries':len(items),'complete_distinct_opportunities':len(uniq),
   'mean_paper_net_pct':round(statistics.fmean(gains),4) if gains else None,
   'worst_pct':round(min(gains),4) if gains else None,
   'evidence':'descriptive_only' if len(uniq)>=min_opportunities else 'insufficient',
   'abstentions_are_zero_exposure':True}
 return output

async def run(limit=1500):
 await init_db()
 async with connection() as c:
  rows=await c.fetch("""SELECT e.candidate_id,e.observed_at,e.hold_minutes,
    a.genome->>'species' species,r.entry_price,r.features
   FROM family_tournament_entries e JOIN family_tournament_ants a USING(run_id,genome_id)
   JOIN research_candidates r ON r.id=e.candidate_id
   WHERE e.run_id=$1 ORDER BY e.candidate_id DESC LIMIT $2""",RUN,limit)
  ids=list({r['candidate_id'] for r in rows})
  pathrows=await c.fetch("""SELECT candidate_id,observed_at,price FROM research_price_path
   WHERE candidate_id=ANY($1::bigint[]) ORDER BY candidate_id,observed_at""",ids) if ids else []
  paths={}
  for p in pathrows:paths.setdefault(p['candidate_id'],[]).append((p['observed_at'],p['price']))
  results=[];features={}
  for r in rows:
   status=simulate(r['observed_at'],float(r['entry_price'] or 0),paths.get(r['candidate_id'],[]),r['hold_minutes'])
   results.append({'candidate_id':r['candidate_id'],'species':r['species'],**status})
   if r['species']=='observation_control' and status['status']=='observed_path':
    vals=r['features']; vals=json.loads(vals) if isinstance(vals,str) else (vals or {})
    for name,v in vals.items():
     if isinstance(v,(int,float)) and not isinstance(v,bool):
      features.setdefault(name,[]).append((float(v),status['net_pct']))
  diagnostics={}
  for name,pairs in features.items():
   if len(pairs)<30:continue
   mid=statistics.median(v for v,_ in pairs)
   hi=[ret for v,ret in pairs if v>mid];lo=[ret for v,ret in pairs if v<=mid]
   if len(hi)<10 or len(lo)<10:continue
   diagnostics[name]={'n':len(pairs),'median_feature':mid,
    'above_mean_pct':round(statistics.fmean(hi),3),
    'below_mean_pct':round(statistics.fmean(lo),3),
    'delta_pct_points':round(statistics.fmean(hi)-statistics.fmean(lo),3),
    'status':'exploratory_correlated_not_predictive_proof'}
 return {'run':RUN,'processed':len(results),'opportunities':len(ids),
  'strategies':summarize(results),'same_candidate_comparisons':matched_edges(results),'feature_splits':diagnostics,
  'caveats':['Different entry filters select different opportunities; raw strategy averages are not causal matched comparisons.',
   'Price sampling is incomplete and provider prices are not executable fills.',
   'Missing signals imply abstention, not a losing or winning trade.',
   'Feature splits are exploratory and cannot be reused as independent validation.'],
  'authority':'read_only_no_breeding_no_live_promotion'}
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str))

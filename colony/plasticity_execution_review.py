"""Read-only executable-evidence and opportunity-cost audit, not a fill model."""
import asyncio,json
from collections import defaultdict
from db import init_db,connection
SQL="""SELECT d.entry_id,d.genome_id,d.action,e.candidate_id,e.observed_at,
 l.net_return_pct,l.paper_pnl_gbp,
 a.status entry_status,a.latency_seconds entry_latency,
 b.status exit_status,b.latency_seconds exit_latency
 FROM plasticity_forward_decisions d JOIN eve_reference_paper_entries e ON e.id=d.entry_id
 LEFT JOIN controlled_paper_trade_ledger l ON l.entry_id=d.entry_id
 LEFT JOIN canary_forward_quote_observations a ON a.entry_id=d.entry_id AND a.phase='entry'
 LEFT JOIN canary_forward_quote_observations b ON b.entry_id=d.entry_id AND b.phase='exit'
 ORDER BY e.observed_at,d.entry_id"""
def classify(row):
 if row['entry_status']=='quoted' and row['exit_status']=='quoted':
  x=row['entry_latency'];y=row['exit_latency']
  if x is not None and y is not None and 0<=x<=2 and 0<=y<=2:return 'timely_pair_not_fill'
  return 'delayed_pair'
 if row['entry_status']=='unavailable' or row['exit_status']=='unavailable':return 'unavailable'
 return 'incomplete_evidence'
def assess(rows):
 # Count a market opportunity once per candidate, while retaining per-genome decisions.
 by=defaultdict(lambda:defaultdict(lambda:{'entries':0,'marked':0,'nominal_gbp':0.,'loss_marks':0,'win_marks':0}))
 abstain=defaultdict(lambda:{'marked':0,'missed_winners':0,'avoided_losers':0,'unmarked':0,'foregone_nominal_gbp':0.})
 distinct=defaultdict(set)
 for r in rows:
  r=dict(r);cls=classify(r);arm=r['action'];z=by[arm][cls];z['entries']+=1
  distinct[cls].add(r['candidate_id'])
  val=r['paper_pnl_gbp']
  if val is not None:
   v=float(val);z['marked']+=1;z['nominal_gbp']+=v
   if v<0:z['loss_marks']+=1
   if v>0:z['win_marks']+=1
   if arm=='abstain':
    a=abstain[r['genome_id']];a['marked']+=1;a['foregone_nominal_gbp']+=v
    if v>0:a['missed_winners']+=1
    elif v<0:a['avoided_losers']+=1
  elif arm=='abstain':abstain[r['genome_id']]['unmarked']+=1
 return {'decision_groups':{a:{k:{**v,'nominal_gbp':round(v['nominal_gbp'],3)} for k,v in s.items()} for a,s in by.items()},
  'independent_candidates_by_evidence':{k:len(v) for k,v in distinct.items()},
  'plasticity_abstention_by_genome':{k:{**v,'foregone_nominal_gbp':round(v['foregone_nominal_gbp'],3)} for k,v in abstain.items()},
  'authority':'read_only_no_promotion','caution':'Missing or delayed quotes cannot demonstrate executable profits; abstention marks are counterfactual.'}
async def run():
 await init_db()
 async with connection() as c:rows=await c.fetch(SQL)
 return assess(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

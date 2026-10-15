"""Strict evidence report: fresh paired quotes by market opportunity, NOT fills."""
import asyncio,json
from collections import defaultdict
from db import init_db,connection
from colony.canary_quote_economics import evaluate
SQL="""SELECT e.candidate_id,e.mint,e.id entry_id,e.genome_id,
 a.quote entry_quote,b.quote exit_quote,
 a.latency_seconds entry_latency,b.latency_seconds exit_latency,
 a.observation_source entry_source,b.observation_source exit_source
 FROM canary_forward_quote_observations a
 JOIN eve_reference_paper_entries e ON e.id=a.entry_id
 JOIN canary_forward_quote_observations b ON b.entry_id=a.entry_id AND b.phase='exit'
 WHERE a.phase='entry' AND a.status='quoted' AND b.status='quoted'
 ORDER BY e.candidate_id,e.id"""
def summarize(rows):
 unique={};counts=defaultdict(int)
 for r in rows:
  r=dict(r);x=evaluate([r]);
  if not x:counts['invalid_quantity_pair']+=1;continue
  fast=(r['entry_latency'] is not None and r['exit_latency'] is not None and
        0<=r['entry_latency']<=2 and 0<=r['exit_latency']<=2)
  counts['timely_pair_rows' if fast else 'delayed_pair_rows']+=1
  key=r['candidate_id'];score=(int(fast),-max(r['entry_latency'] or 999,r['exit_latency'] or 999))
  if key not in unique or score>unique[key][0]:unique[key]=(score,r,x[0])
 timely=[v for v in unique.values() if v[0][0]==1]
 return {'paired_rows':sum(counts.values()),'distinct_candidate_opportunities':len(unique),
  'timely_distinct_candidates':len(timely),'timely_threshold_seconds':2,
  'minimum_timely_independent_candidates':25,
  'research_gate_met':len(timely)>=25,
  'timely_indicative_quote_net_pct':[v[2]['net_pct'] for v in timely],
  'diagnostic_counts':dict(counts),
  'sources':{s:sum(1 for _,r,_ in unique.values() if (r['exit_source'] or 'legacy_unknown')==s) for s in sorted({r['exit_source'] or 'legacy_unknown' for _,r,_ in unique.values()})},
  'authority':'read_only_never_promote','note':'Quote economics are not fills; positivity or 25 opportunities alone does not authorise live trading.'}
async def run():
 await init_db()
 async with connection() as c:rows=await c.fetch(SQL)
 return summarize(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

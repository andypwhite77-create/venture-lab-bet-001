"""Diagnostic progression toward Canary consideration; NEVER grants trading authority."""
import asyncio,json
from db import init_db,connection
from colony.canary_candidate_review import SQL,assess
from colony.canary_quote_economics import evaluate

async def run():
 await init_db()
 async with connection() as c:
  candidates=[assess(r) for r in await c.fetch(SQL)]
  quote_rows=await c.fetch("""SELECT e.genome_id,e.candidate_id,a.entry_id,a.quote entry_quote,b.quote exit_quote,
   a.latency_seconds entry_latency,b.latency_seconds exit_latency
   FROM canary_forward_quote_observations a
   JOIN eve_reference_paper_entries e ON e.id=a.entry_id
   JOIN canary_forward_quote_observations b ON b.entry_id=a.entry_id AND b.phase='exit'
   WHERE a.phase='entry' AND a.status='quoted' AND b.status='quoted'""")
  stats={}
  for r in quote_rows:
   x=evaluate([dict(r)])
   if not x:continue
   z=stats.setdefault(r['genome_id'],{'paired_candidates':set(),'fast_candidates':set(),'indicative_net':[]})
   z['paired_candidates'].add(r['candidate_id'])
   if r['entry_latency'] is not None and r['exit_latency'] is not None and max(r['entry_latency'],r['exit_latency'])<=2:
    z['fast_candidates'].add(r['candidate_id']);z['indicative_net'].append(x[0]['net_pct'])
  ranked=[]
  for r in candidates:
   q=stats.get(r['genome_id'],{'paired_candidates':set(),'fast_candidates':set(),'indicative_net':[]})
   vals=q['indicative_net'];fast=len(q['fast_candidates'])
   stage='historical_repair' if r['tier']!='research_shortlist' else 'forward_challenger_candidate'
   blockers=list(r['blockers'])
   if fast<25:blockers.append('less_than_25_timely_distinct_quote_opportunities')
   if fast>=25 and (sum(vals)/len(vals) if vals else -999)<=0:blockers.append('nonpositive_timely_quote_economics')
   blockers.append('no_spartan_qualification')
   ranked.append({'genome_id':r['genome_id'],'source':r['source'],'stage':stage,'distinct_completed_mints':r['completed'],
    'capped_mean_mark_pct':r['capped_mean_pct'],'median_mark_pct':r['median_mark_pct'],
    'paired_quote_candidates':len(q['paired_candidates']),'timely_quote_candidates':fast,
    'blockers':list(dict.fromkeys(blockers)),'authority':'no_promotion'})
  ranked.sort(key=lambda r:(r['stage']=='forward_challenger_candidate',r['timely_quote_candidates'],r['distinct_completed_mints']),reverse=True)
  return {'reviewed':len(ranked),'canary_nominees':0,'top_diagnostics':ranked[:12],
   'promotion_rule':'Candidate audit, distinct timely quote coverage, positive fully-costed forward P/L, Spartan pass and explicit approval all required; never automated.'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

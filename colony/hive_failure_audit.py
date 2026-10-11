"""Read-only research-method audit; does not train on Spartan examiner answers."""
import asyncio,json,statistics
from db import init_db,connection
def diagnose(scores):
 if not scores:return {'status':'no_matched_evidence'}
 return {'status':'descriptive_only','opportunity_count':len(set(x['opportunity_id'] for x in scores)),
 'individual_challengers':len(set(x['challenger_genome_id'] for x in scores)),
 'do_not_treat_correlated_pairs_as_independent':True}
async def run():
 await init_db()
 async with connection() as c:
  campaigns=await c.fetch("""SELECT id,created_at,summary->>'methodology_version' methodology,
   (summary->>'tested')::int tested,
   (summary->>'holdout_positive')::int holdout_positive,
   jsonb_array_length(finalists) finalists,
   summary->>'historical_holdout_used_for_algorithm_design' holdout_methodology_leak
   FROM historical_nursery_runs WHERE family='queen_pattern' ORDER BY id DESC LIMIT 10""")
  pairs=await c.fetch("""SELECT p.opportunity_id,p.challenger_genome_id,p.challenger_net_pct,p.control_net_pct,
    a.genome->'parameters' parameters
    FROM hive_forward_pairs p JOIN family_tournament_ants a
     ON a.genome_id=p.challenger_genome_id AND a.run_id=split_part(p.opportunity_id,':',1)
    WHERE p.experiment_id=1 ORDER BY p.challenger_genome_id,p.opportunity_id""")
  groups={}
  for r in pairs:groups.setdefault(r['challenger_genome_id'],[]).append(dict(r))
  individual=[]
  for gid,rr in groups.items():
   ch=[float(x['challenger_net_pct']) for x in rr];co=[float(x['control_net_pct']) for x in rr]
   individual.append({'genome_id':gid,'n_opportunities':len(set(x['opportunity_id'] for x in rr)),
     'mean_challenger_net_pct':round(statistics.fmean(ch),4),
     'mean_control_net_pct':round(statistics.fmean(co),4),
     'mean_edge_pct_points':round(statistics.fmean(a-b for a,b in zip(ch,co)),4),
     'worst_challenger_pct':round(min(ch),4),'parameters':json.loads(rr[0]['parameters']) if isinstance(rr[0]['parameters'],str) else rr[0]['parameters']})
  individual.sort(key=lambda x:x['mean_edge_pct_points'],reverse=True)
  return {'campaigns':[dict(x) for x in campaigns],
   'paired_study':diagnose(pairs),'challengers':individual,
   'findings':['Exit stop-loss and take-profit thresholds are NOT modeled by research_outcomes horizon returns; only hold_minutes affects this forward comparison. Identical-return variants must not be credited as evidence of exit-policy success.',
   'Different holding horizons compared on identical candidate arrivals are descriptive shadow estimates, not actual risk-controlled execution.',
   'Historical holdout acknowledged as used in algorithm development; do not use it as clean proof for another round of selection.',
   'Pause broad breeding; prioritise causal exit simulator and new independent future observations.'],
   'recommendation':'Maintain Campaign 49 quality gate; validate actual stop/take intrahorizon paths with independent quotes before claiming risk-tail correction.',
   'execution_authority':'none','spartan_exam_answers_used':False}
if __name__=='__main__':print(json.dumps(asyncio.run(run()),default=str,indent=2))

"""Prospective paired challenger-vs-control scorecard. Research only.
Observations must be from later market opportunities, never historical holdout.
This processor does not invent observations or automatically grant qualification.
"""
import asyncio,json
from db import init_db,connection
SCHEMA="""CREATE TABLE IF NOT EXISTS hive_forward_pairs(
 id BIGSERIAL PRIMARY KEY,experiment_id BIGINT NOT NULL REFERENCES hive_experiments(id),
 opportunity_id TEXT NOT NULL,observed_at TIMESTAMPTZ NOT NULL,
 challenger_genome_id TEXT NOT NULL,control_genome_id TEXT NOT NULL,
 challenger_net_pct DOUBLE PRECISION NOT NULL,control_net_pct DOUBLE PRECISION NOT NULL,
 source TEXT NOT NULL CHECK(source IN ('prospective_paper','forward_shadow')),
 recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(experiment_id,opportunity_id,challenger_genome_id,control_genome_id));
CREATE TABLE IF NOT EXISTS hive_forward_score_runs(
 id BIGSERIAL PRIMARY KEY,experiment_id BIGINT NOT NULL REFERENCES hive_experiments(id),
 assessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),assessment TEXT NOT NULL,
 evidence JSONB NOT NULL);"""
def assess(pairs,minimum=30):
 if len(pairs)<minimum:return {'status':'insufficient_evidence','pairs':len(pairs),'required':minimum}
 ch=[float(x['challenger_net_pct']) for x in pairs]
 co=[float(x['control_net_pct']) for x in pairs]
 avg_ch=sum(ch)/len(ch);avg_co=sum(co)/len(co)
 tail_ch=min(ch);tail_co=min(co)
 good=avg_ch>0 and avg_ch>avg_co and tail_ch>tail_co
 bad=avg_ch<=avg_co or (avg_ch<=0 and tail_ch<=tail_co)
 return {'status':'supported_paper' if good else ('failed_paper' if bad else 'inconclusive'),
 'pairs':len(pairs),'challenger_avg_net_pct':avg_ch,'control_avg_net_pct':avg_co,
 'challenger_worst_pct':tail_ch,'control_worst_pct':tail_co,
 'note':'Paper-only paired outcome; not permission to trade or claim live uplift'}
async def run():
 await init_db();out=[]
 async with connection() as c:
  await c.execute(SCHEMA)
  experiments=await c.fetch("SELECT id,created_at,minimum_forward_trades FROM hive_experiments WHERE status='awaiting_prospective_test'")
  for e in experiments:
   # Enforce creation timestamp: past data never qualifies as prospective.
   rows=await c.fetch("""SELECT challenger_net_pct,control_net_pct FROM hive_forward_pairs
      WHERE experiment_id=$1 AND observed_at>$2 ORDER BY observed_at LIMIT 2000""",e['id'],e['created_at'])
   result=assess(rows,e['minimum_forward_trades'])
   if result['status']!='insufficient_evidence':
    await c.execute("INSERT INTO hive_forward_score_runs(experiment_id,assessment,evidence) VALUES($1,$2,$3::jsonb)",e['id'],result['status'],json.dumps(result))
    # Paper success never automatically marks the economic experiment as proven:
    # its prediction explicitly requires later realised live evidence.
   out.append({'experiment_id':e['id'],**result})
 return out
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

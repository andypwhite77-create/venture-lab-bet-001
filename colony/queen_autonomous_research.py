"""Read-only adversarial research council: proposer -> critic -> human review.

LLM cannot issue tools or choose external URLs. Every factual signal is an
aggregate computed from our DB; novel external theses remain unverified.
"""
import asyncio,json,os,time,httpx
from db import connection,init_db
from colony.queen_opportunity_queue import ensure_schema,submit,KINDS
from colony.queen_roles import HIVE_CREED

MODEL=os.getenv('SWARM_STRATEGIC_MODEL','qwen3:1.7b')
URL=os.getenv('OLLAMA_URL','http://127.0.0.1:11434/api/generate')
SCHEMA="""CREATE TABLE IF NOT EXISTS queen_autonomous_research_runs (
 id BIGSERIAL PRIMARY KEY,started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 status TEXT NOT NULL DEFAULT 'running',snapshot JSONB NOT NULL DEFAULT '{}',
 proposer JSONB,critic JSONB,proposal_id BIGINT,errors JSONB NOT NULL DEFAULT '[]'
);"""
async def _inference(prompt,max_tokens=400):
 async with httpx.AsyncClient(timeout=90) as client:
  r=await client.post(URL,json={'model':MODEL,'prompt':prompt,'stream':False,'format':'json','think':False,
  'options':{'num_ctx':2048,'num_predict':max_tokens,'temperature':0.25}})
  r.raise_for_status()
  val=json.loads(r.json()['response'])
  if not isinstance(val,dict):raise ValueError('invalid_model_response')
  return val
async def snapshot(conn):
 routes=await conn.fetchrow("""SELECT count(*)::int total,
 count(*) FILTER(WHERE status='rejected' AND reason IN ('gateway_no_route_found','quote_price_impact'))::int route_blocked,
 count(*) FILTER(WHERE status='closed' AND broadcast)::int closed
 FROM canary_trade_intents WHERE created_at>=now()-interval '7 days'""")
 providers=await conn.fetch("""SELECT provider, count(*)::int observations,
 count(*) FILTER(WHERE success=false)::int failures
 FROM colony_market_ingress WHERE observed_at>=now()-interval '7 days'
 GROUP BY provider ORDER BY observations DESC LIMIT 6""")
 shadow=await conn.fetchrow("""SELECT run_at,results FROM capital_preservation_shadow_runs ORDER BY id DESC LIMIT 1""")
 live=await conn.fetchrow("""SELECT count(*)::int trades,
   coalesce(sum((execution->>'realized_market_pnl_after_network_fees_sol')::numeric),0)::float8 net_sol
   FROM canary_trade_intents WHERE status='closed' AND broadcast
   AND execution ? 'realized_market_pnl_after_network_fees_sol'
   AND created_at>=now()-interval '7 days'""")
 # No sealed examiner outcomes or private wallets sent to the model.
 return {'window':'last_7_days','canary_intents':dict(routes),
         'provider_health':[dict(p) for p in providers],
         'realized_canary_economics':dict(live),'rent_recovery_excluded':True,
         'shadow_filter':dict(shadow) if shadow else None,
         'source_tables':['canary_trade_intents','colony_market_ingress','capital_preservation_shadow_runs'],
         'note':'Observed records, not complete market coverage. No verified external major-asset evidence.'}
def validate(proposal,critique,snap):
 kind=str(proposal.get('kind',''))
 title=str(proposal.get('title','')).strip()
 thesis=str(proposal.get('thesis','')).strip()
 failures=proposal.get('failure_modes')
 if kind not in KINDS or len(title)<8 or len(thesis)<20 or not isinstance(failures,list) or not failures:return None
 # Major asset / cross-venue opportunity cannot be called validated from SOL ops evidence.
 if kind in ('major_asset_short','cross_venue_arbitrage'):return None
 if critique.get('research_appropriate') is not True:return None
 critical=critique.get('objections')
 if not isinstance(critical,list) or not critical:return None
 risks=[str(x)[:200] for x in (failures+critical) if str(x).strip()][:8]
 return {'kind':kind,'title':title[:160],'thesis':thesis[:3000],
         'risks':risks,'evidence':{'source':'queen_autonomous_research_snapshot','snapshot':snap,
            'status':'hypothesis_not_independently_verified'},
         'resources':{'scope':'human-approved research only; no trading or subscriptions'}}
async def run():
 await init_db()
 async with connection() as c:
  await ensure_schema(c);await c.execute(SCHEMA)
  rec=await c.fetchrow("""INSERT INTO queen_autonomous_research_runs(snapshot)
    VALUES('{}'::jsonb) RETURNING id""")
  run_id=rec['id']; s=await snapshot(c)
  await c.execute('UPDATE queen_autonomous_research_runs SET snapshot=$2::jsonb WHERE id=$1',run_id,json.dumps(s,default=str))
 try:
  proposer=await _inference('You are Swarm Queen. '+HIVE_CREED+' Form ONE specific research-only hypothesis grounded exclusively in the JSON evidence below, not invented market information. Stay within Solana execution research, feed reliability, or bounded research infrastructure. No market manipulation, trading or system access. JSON keys: kind, title, thesis, failure_modes (array of 2-4 strings). Kinds: market_dislocation, research_infrastructure, colony_expansion, other. Evidence: '+json.dumps(s,default=str)[:3300],480)
  critic=await _inference('You are an independent adversarial examiner. Find weaknesses, confounding and missing evidence. Reject speculative assertions presented as established facts. Do not use Spartan/holdout data. Respond JSON with research_appropriate (boolean), objections (array of strings), strongest_counterargument (string). Hypothesis: '+json.dumps(proposer)[:1900]+' Observations: '+json.dumps(s,default=str)[:2500],360)
  approved=validate(proposer,critic,s)
  async with connection() as c:
   pid=None
   if approved:
    exists=await c.fetchval("""SELECT 1 FROM queen_opportunity_proposals WHERE submitted_by='swarm_queen_council'
       AND title=$1 AND created_at>=now()-interval '7 days' LIMIT 1""",approved['title'])
    if not exists:
     pid=await submit(c,approved['kind'],approved['title'],approved['thesis'],
      'swarm_queen_council',approved['evidence'],approved['risks'],approved['resources'],
      'Independent critic reviewed; unresolved objections included. Research only.')
   await c.execute("""UPDATE queen_autonomous_research_runs
       SET status=$2,proposer=$3::jsonb,critic=$4::jsonb,proposal_id=$5 WHERE id=$1""",
       run_id,'proposed' if pid else 'critic_rejected_or_duplicate',
       json.dumps(proposer),json.dumps(critic),pid)
  return {'run_id':run_id,'status':'proposed' if pid else 'critic_rejected_or_duplicate','proposal_id':pid}
 except Exception as ex:
  async with connection() as c:
   await c.execute("""UPDATE queen_autonomous_research_runs SET status='error',
     errors=$2::jsonb WHERE id=$1""",run_id,json.dumps([type(ex).__name__]))
  return {'run_id':run_id,'status':'error','error':type(ex).__name__}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

"""Low-frequency larger-model strategic review for Swarm Queen.
Runs in the host-network Swarm service while Breeding Queen waits at a campaign boundary.
Research-safe and advisory only: raw LLM output never directly controls breeding or Spartan.
"""
import json, os, time, httpx
from db import connection
from colony.swarm_queen import evidence, ensure_schema

MODEL=os.getenv('SWARM_STRATEGIC_MODEL','qwen3:4b')
OLLAMA=os.getenv('OLLAMA_URL','http://127.0.0.1:11434/api/generate')

async def ensure_request_schema(c):
    await c.execute('''CREATE TABLE IF NOT EXISTS swarm_strategy_requests(
      id BIGSERIAL PRIMARY KEY,
      campaign INTEGER NOT NULL UNIQUE,
      requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      status TEXT NOT NULL DEFAULT 'pending',
      result JSONB)''')

def _safe_snapshot(e):
    q=dict(e.get('queen_research') or {})
    allowed_q={k:q.get(k) for k in (
        'behaviour_groups','largest_behaviour_fraction','behaviour_hhi','behaviour_entropy','effective_behaviours',
        'behaviour_novelty_vs_previous','sensor_combo_count','sensor_combo_hhi','hold_diversity','risk_control_diversity',
        'graveyard_revisit_fraction','career_history_feature_agreement','top_behaviour_group_sizes','holds','risk_controls',
        'top_sensors','preferred_features','underexplored_features','graveyard_niches','career_parent_templates',
        'career_preferred_features','current_ecology_plan','sensor_availability','active_sensor_count','breeding_regime_coverage','weak_niches')}
    return {'queen_research':allowed_q,'constitution':e.get('constitution',{})}

def _prompt(s):
    return ("You are the strategic brain of Swarm Queen. Analyse only the supplied research-safe evolutionary ecology. "
            "Never request or infer sealed holdout/Spartan answers. Never alter evidence gates, capital authority, or individual genomes. "
            "Look for search traps, monoculture, stale niches, sensor blind spots, over/under-exploitation, and testable ways to increase useful variation. "
            "Return JSON with diagnosis (max 80 words), priorities (max 5 strings), experiments (max 5 strings), warnings (max 4 strings). "
            "All suggestions are advisory and must be testable with breeding-visible evidence. Data: "+json.dumps(s,separators=(',',':'))[:5000])

async def review(campaign:int):
    async with connection() as c:
        await ensure_schema(c); e=await evidence(c)
    safe=_safe_snapshot(e); started=time.time()
    out={'campaign':campaign,'model':MODEL,'status':'unavailable','diagnosis':'','priorities':[],'experiments':[],'warnings':[]}
    try:
        async with httpx.AsyncClient(timeout=150) as h:
            r=await h.post(OLLAMA,json={'model':MODEL,'prompt':_prompt(safe),'stream':False,'format':'json','think':False,
                                       'options':{'num_ctx':2048,'num_predict':350,'temperature':0.15}})
            r.raise_for_status(); x=json.loads(r.json()['response'])
        if isinstance(x,dict):
            out.update({k:x.get(k,out[k]) for k in ('diagnosis','priorities','experiments','warnings')})
            out['status']='ok'
    except Exception as ex:
        out['status']='error'; out['warnings']=[repr(ex)[:220]]
    out['seconds']=round(time.time()-started,2); out['updated_at']=time.time()
    async with connection() as c:
        await ensure_schema(c)
        await c.execute("INSERT INTO swarm_queen_journal(model,status,briefing,input_snapshot) VALUES($1,$2,$3::jsonb,$4::jsonb)",
                        MODEL,'strategic_'+out['status'],json.dumps(out),json.dumps(safe,default=str))
    return out

async def process_pending():
    async with connection() as c:
        await ensure_request_schema(c)
        req=await c.fetchrow("""UPDATE swarm_strategy_requests SET status='running',started_at=now()
          WHERE id=(SELECT id FROM swarm_strategy_requests WHERE status='pending' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED)
          RETURNING id,campaign""")
    if not req:return None
    out=await review(int(req['campaign']))
    async with connection() as c:
        await c.execute("UPDATE swarm_strategy_requests SET status=$2,result=$3::jsonb,completed_at=now() WHERE id=$1",
                        req['id'],'complete' if out.get('status')=='ok' else 'error',json.dumps(out))
    return out

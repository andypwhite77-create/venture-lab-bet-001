"""Low-frequency larger-model strategic review for Swarm Queen.
Runs in the host-network Swarm service while Breeding Queen waits at a campaign boundary.
Research-safe and advisory only: raw LLM output never directly controls breeding or Spartan.
"""
import json, os, time, httpx
from db import connection
from colony.swarm_queen import evidence, ensure_schema
from colony.queen_roles import SWARM_QUEEN, ROLE_VERSION, HIVE_CREED

MODEL=os.getenv('SWARM_STRATEGIC_MODEL','qwen3:1.7b')
OLLAMA=os.getenv('OLLAMA_URL','http://127.0.0.1:11434/api/generate')
STRATEGIC_TIMEOUT_SECONDS=max(60,int(os.getenv('SWARM_STRATEGIC_TIMEOUT_SECONDS','120')))

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
    candidates=[]
    for k in list(q.get('career_preferred_features') or [])+list(q.get('preferred_features') or [])+list(q.get('underexplored_features') or [])+list((q.get('top_sensors') or {}).keys()):
        if k not in candidates:candidates.append(k)
    quality=[]
    for x in (q.get('quality_history') or [])[-4:]:
        quality.append({k:x.get(k) for k in ('finalists','behaviour_groups','median_train_n','median_validation_n','median_concentration','median_predicates','median_selection_score')})
    exams=[]
    for x in (q.get('exam_history') or [])[-5:]:
        exams.append({'survivors':x.get('spartan_survivors',0),'distinct':x.get('distinct_survivor_behaviours',0),'finalists':x.get('finalists',0)})
    return {'ecology':{k:q.get(k) for k in ('behaviour_groups','largest_behaviour_fraction','behaviour_hhi','behaviour_entropy','effective_behaviours','behaviour_novelty_vs_previous','hold_diversity','risk_control_diversity','career_history_feature_agreement','spartan_drought_campaigns')},
            'candidate_sensors':candidates[:20],'quality_history':quality,'exam_history':exams,
            'prospective':q.get('prospective_experience_summary',{}),'career_parent_templates':q.get('career_parent_templates',0),
            'constitution':e.get('constitution',{})}

STRATEGY_SCHEMA={
  'type':'object',
  'properties':{
    'diagnosis':{'type':'string'},
    'mode':{'type':'string','enum':['diversify','balanced','exploit']},
    'focus_sensors':{'type':'array','items':{'type':'string'},'maxItems':6},
    'avoid_sensors':{'type':'array','items':{'type':'string'},'maxItems':4}},
  'required':['diagnosis','mode','focus_sensors','avoid_sensors']}

def _prompt(s):
    return ("You are Swarm Queen, strategic research director for an evolutionary trading research system. "+HIVE_CREED+" "
            "Breeding Queen is the sole genome factory. Never spawn or mutate ants, promote challengers, trade, or allocate real capital. "
            "Use only the supplied research-safe evidence. Never infer sealed holdout or Spartan thresholds. "
            "Return ONLY valid JSON with exactly these keys: diagnosis (string under 30 words), mode (diversify, balanced, or exploit), "
            "focus_sensors (array, max 6 observable sensor names), avoid_sensors (array, max 4 observable sensor names). "
            "Choose actions that improve breadth, robustness, behavioural diversity, and prospective career quality over repeated campaigns. Data: "
            +json.dumps(s,separators=(',',':'))[:3000])

async def review(campaign:int):
    async with connection() as c:
        await ensure_schema(c); e=await evidence(c)
    safe=_safe_snapshot(e); started=time.time()
    out={'campaign':campaign,'model':MODEL,'role_version':ROLE_VERSION,'role':SWARM_QUEEN,'status':'unavailable','diagnosis':'','priorities':[],'experiments':[],'warnings':[],
         'research_adjustments':{'mode':'balanced','focus_sensors':[],'avoid_sensors':[]}}
    try:
        async with httpx.AsyncClient(timeout=STRATEGIC_TIMEOUT_SECONDS) as h:
            r=await h.post(OLLAMA,json={'model':MODEL,'prompt':_prompt(safe),'stream':False,'format':STRATEGY_SCHEMA,'think':False,
                                       'keep_alive':'30m','options':{'num_ctx':1024,'num_predict':180,'temperature':0.0}})
            r.raise_for_status(); x=json.loads(r.json()['response'])
        if isinstance(x,dict):
            out['diagnosis']=str(x.get('diagnosis',''))[:240]
            mode=str(x.get('mode','balanced')).lower()
            if mode not in ('diversify','balanced','exploit'): mode='balanced'
            out['research_adjustments']={'mode':mode,
                'focus_sensors':list(x.get('focus_sensors') or [])[:6],
                'avoid_sensors':list(x.get('avoid_sensors') or [])[:4]}
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
        # Recover only genuinely stale work after a daemon/container interruption.
        await c.execute("UPDATE swarm_strategy_requests SET status='pending',started_at=NULL WHERE status='running' AND started_at < now()-interval '10 minutes'")
        req=await c.fetchrow("""UPDATE swarm_strategy_requests SET status='running',started_at=now()
          WHERE id=(SELECT id FROM swarm_strategy_requests WHERE status='pending' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED)
          RETURNING id,campaign""")
    if not req:return None
    out=await review(int(req['campaign']))
    async with connection() as c:
        await c.execute("UPDATE swarm_strategy_requests SET status=$2,result=$3::jsonb,completed_at=now() WHERE id=$1",
                        req['id'],'complete' if out.get('status')=='ok' else 'error',json.dumps(out))
    return out

"""Advisory Swarm Queen recovery classifier.

Produces auditable market-regime advice for live inventory recovery. It has no
wallet, Gateway, signing, Canary-control or execution authority. Shadow and
operational requests use the same classifier; only the executor may act on advice.
"""
import json, os, time
from datetime import datetime, timezone
import httpx
from db import connection

MODEL=os.getenv('SWARM_RECOVERY_MODEL',os.getenv('SWARM_STRATEGIC_MODEL','qwen3:1.7b'))
OLLAMA=os.getenv('OLLAMA_URL','http://127.0.0.1:11434/api/generate')
TIMEOUT=max(20,int(os.getenv('SWARM_RECOVERY_TIMEOUT_SECONDS','60')))

RESULT_SCHEMA={
  'type':'object',
  'properties':{
    'classification':{'type':'string','enum':['NORMAL_FLUCTUATION','GENUINE_SLIDE','UNCERTAIN']},
    'confidence':{'type':'number','minimum':0,'maximum':1},
    'reason':{'type':'string','maxLength':180},
    'evidence_keys':{'type':'array','items':{'type':'string'},'maxItems':6}},
  'required':['classification','confidence','reason','evidence_keys']}

async def ensure_schema(c):
    await c.execute('''CREATE TABLE IF NOT EXISTS recovery_assessment_requests(
      id BIGSERIAL PRIMARY KEY,intent_id BIGINT NOT NULL,
      requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,status TEXT NOT NULL DEFAULT 'pending',
      shadow BOOLEAN NOT NULL DEFAULT true,assessment_kind TEXT NOT NULL DEFAULT 'deadline',
      evidence JSONB NOT NULL DEFAULT '{}',result JSONB NOT NULL DEFAULT '{}');
      ALTER TABLE recovery_assessment_requests ADD COLUMN IF NOT EXISTS assessment_kind TEXT NOT NULL DEFAULT 'deadline';
      CREATE INDEX IF NOT EXISTS recovery_assessment_intent_idx
      ON recovery_assessment_requests(intent_id,requested_at DESC);''')

def _obj(x):
    if isinstance(x,dict): return x
    if isinstance(x,str):
        try:return json.loads(x)
        except Exception:return {}
    return {}

def _pct(n,d):
    try:
        n=float(n);d=float(d)
        return None if not d else 100.0*n/d
    except Exception:return None

def _quote_out(q):
    q=_obj(q)
    try:return float(q.get('minAmountOut') or q.get('amountOut'))
    except Exception:return None

def _market_point(row):
    if not row:return None
    m=_obj(row['market']);f=_obj(row['features'])
    return {
      'candidate_id':int(row['id']),'observed_at':row['created_at'].isoformat(),
      'price_usd':m.get('price_usd'),'liquidity_usd':m.get('liquidity_usd',f.get('liquidity_usd')),
      'price_change_m5':m.get('price_change_m5',f.get('price_change_m5')),
      'price_change_h1':m.get('price_change_h1',f.get('price_change_h1')),
      'dex_buy_ratio_m5':f.get('dex_buy_ratio_m5'),
      'volume_m5':m.get('volume_m5',f.get('volume_m5')),
      'buys_m5':m.get('buys_m5'),'sells_m5':m.get('sells_m5'),
      'buys_h1':m.get('buys_h1'),'sells_h1':m.get('sells_h1')}

async def build_snapshot(c,intent_id:int,assessment_kind:str='deadline'):
    row=await c.fetchrow('''SELECT id,candidate_id,mint,status,reason,observed_at,
      execution,updated_at FROM canary_trade_intents WHERE id=$1''',intent_id)
    if not row: raise ValueError('intent_not_found')
    data=_obj(row['execution']); basis=float(data.get('entry_trade_sol') or 0)
    candidate=await c.fetchrow('SELECT id,created_at,features,market FROM research_candidates WHERE id=$1',row['candidate_id'])
    deadline=data.get('recovery_deadline')
    if assessment_kind=='current': cutoff=datetime.now(timezone.utc)
    elif assessment_kind=='deadline': cutoff=datetime.fromtimestamp(float(deadline),timezone.utc) if deadline else row['updated_at']
    else: raise ValueError('assessment_kind')
    later=await c.fetch('''SELECT id,created_at,features,market FROM research_candidates
      WHERE mint=$1 AND created_at >= $2 AND created_at <= $3 ORDER BY created_at LIMIT 12''',row['mint'],row['observed_at'],cutoff)
    points=[_market_point(x) for x in later]
    entry_point=_market_point(candidate)
    latest_point=points[-1] if points else entry_point
    strategy_pnl=data.get('strategy_horizon_pnl_sol')
    best_pnl=data.get('recovery_best_pnl_sol')
    last_pnl=data.get('recovery_last_pnl_sol')
    evidence={
      'intent_id':int(row['id']),'candidate_id':int(row['candidate_id']),
      'status':row['status'],'reason':row['reason'],'mint':row['mint'],
      'evidence_cutoff':cutoff.isoformat(),'assessment_kind':assessment_kind,'snapshot_policy':('current_reassessment' if assessment_kind=='current' else 'strict_recovery_deadline_no_lookahead'),
      'entry_trade_sol':basis,'strategy_horizon_pnl_pct':_pct(strategy_pnl,basis),
      'recovery_best_pnl_pct':_pct(best_pnl,basis),'recovery_last_pnl_pct':_pct(last_pnl,basis),
      'strategy_exit_min_sol':_quote_out(data.get('strategy_exit_quote')),
      'recovery_best_min_sol':_quote_out(data.get('recovery_best_quote')),
      'recovery_last_min_sol':_quote_out(data.get('recovery_last_quote')),
      'recovery_last_reason':data.get('recovery_last_reason'),
      'recovery_exit_reason':data.get('recovery_exit_reason'),
      'exit_prebroadcast_rejection':data.get('exit_prebroadcast_rejection'),
      'entry_market':entry_point,'market_path':points,'latest_market':latest_point}
    return _derive(evidence)

def _derive(e):
    entry=e.get('entry_market') or {}; latest=e.get('latest_market') or {}
    ep=entry.get('price_usd'); lp=latest.get('price_usd')
    el=entry.get('liquidity_usd'); ll=latest.get('liquidity_usd')
    e['price_change_since_entry_pct']=None if not ep or lp is None else 100.0*(float(lp)/float(ep)-1.0)
    e['liquidity_change_since_entry_pct']=None if not el or ll is None else 100.0*(float(ll)/float(el)-1.0)
    s=e.get('strategy_exit_min_sol'); b=e.get('recovery_best_min_sol'); last=e.get('recovery_last_min_sol')
    e['recovery_improvement_vs_horizon_pct']=None if not s or b is None else 100.0*(float(b)/float(s)-1.0)
    e['last_improvement_vs_horizon_pct']=None if not s or last is None else 100.0*(float(last)/float(s)-1.0)
    flags=[]
    if e['liquidity_change_since_entry_pct'] is not None and e['liquidity_change_since_entry_pct']<=-50: flags.append('liquidity_down_50pct')
    if latest.get('price_change_h1') is not None and float(latest['price_change_h1'])<=-50: flags.append('h1_down_50pct')
    if latest.get('dex_buy_ratio_m5') is not None and float(latest['dex_buy_ratio_m5'])<0.35: flags.append('buyers_below_35pct_m5')
    if e.get('recovery_last_reason') and 'price_impact' in str(e['recovery_last_reason']): flags.append('exit_price_impact_rejected')
    e['danger_flags']=flags
    return e

def _parse_model_json(value):
    if isinstance(value,dict): return value
    text=str(value or '').strip()
    if text.startswith('```'):
        text=text.strip('`').strip()
        if text.lower().startswith('json'): text=text[4:].lstrip()
    try:return json.loads(text)
    except Exception:
        a=text.find('{');b=text.rfind('}')
        if a>=0 and b>a:return json.loads(text[a:b+1])
        raise

def _model_snapshot(e):
    return {
      'assessment_kind':e.get('assessment_kind'),'status':e.get('status'),'reason':e.get('reason'),
      'strategy_horizon_pnl_pct':e.get('strategy_horizon_pnl_pct'),
      'recovery_best_pnl_pct':e.get('recovery_best_pnl_pct'),'recovery_last_pnl_pct':e.get('recovery_last_pnl_pct'),
      'recovery_improvement_vs_horizon_pct':e.get('recovery_improvement_vs_horizon_pct'),
      'last_improvement_vs_horizon_pct':e.get('last_improvement_vs_horizon_pct'),
      'entry_market':e.get('entry_market'),'latest_market':e.get('latest_market'),
      'price_change_since_entry_pct':e.get('price_change_since_entry_pct'),
      'liquidity_change_since_entry_pct':e.get('liquidity_change_since_entry_pct'),
      'current_quote':e.get('current_quote'),'danger_flags':e.get('danger_flags',[]),
      'recovery_last_reason':e.get('recovery_last_reason'),'recovery_exit_reason':e.get('recovery_exit_reason'),
      'exit_prebroadcast_rejection':e.get('exit_prebroadcast_rejection')}

def _prompt(e):
    return ("You are Swarm Queen acting only as an advisory market-regime classifier for an already-open tiny Solana microcap position. "
      "You cannot trade, sign, change risk limits, or control the wallet. Classify whether the evidence best fits NORMAL_FLUCTUATION, GENUINE_SLIDE, or UNCERTAIN. "
      "NORMAL_FLUCTUATION means a recoverable-looking move where waiting for a small profitable safe exit is reasonable. GENUINE_SLIDE means deterioration where delaying exit materially increases bag-holder risk. "
      "UNCERTAIN means evidence is insufficient or conflicting. Be conservative with missing/failed data. Do not infer facts outside the evidence. "
      "Reason must be under 24 words. evidence_keys must name supplied fields, not invent facts. Return only the requested JSON. Evidence: "+json.dumps(_model_snapshot(e),separators=(',',':'),default=str)[:3500])

async def enqueue(intent_id:int,assessment_kind:str='deadline'):
    async with connection() as c:
        await ensure_schema(c)
        evidence=await build_snapshot(c,intent_id,assessment_kind)
        existing=await c.fetchval("""SELECT id FROM recovery_assessment_requests
          WHERE intent_id=$1 AND assessment_kind=$2 AND status IN ('pending','running') ORDER BY id DESC LIMIT 1""",intent_id,assessment_kind)
        if existing:return int(existing)
        return int(await c.fetchval("INSERT INTO recovery_assessment_requests(intent_id,assessment_kind,evidence) VALUES($1,$2,$3::jsonb) RETURNING id",intent_id,assessment_kind,json.dumps(evidence,default=str)))

async def review(evidence,shadow=True):
    shadow=bool(shadow)
    started=time.time(); out={'classification':'UNCERTAIN','confidence':0.0,'reason':'classifier_unavailable','evidence_keys':[],'model':MODEL,'shadow':shadow,'mode':'shadow' if shadow else 'operational'}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as h:
            r=await h.post(OLLAMA,json={'model':MODEL,'prompt':_prompt(evidence),'stream':False,'format':RESULT_SCHEMA,'think':False,
              'keep_alive':'30m','options':{'num_ctx':2048,'num_predict':220,'temperature':0.0}})
            r.raise_for_status(); x=_parse_model_json(r.json().get('response'))
        cls=str(x.get('classification','UNCERTAIN'))
        if cls not in ('NORMAL_FLUCTUATION','GENUINE_SLIDE','UNCERTAIN'): cls='UNCERTAIN'
        out.update(classification=cls,confidence=max(0.0,min(1.0,float(x.get('confidence',0)))),
          reason=str(x.get('reason',''))[:300],evidence_keys=[str(v)[:80] for v in list(x.get('evidence_keys') or [])[:6]])
    except Exception as ex:
        out['reason']='classifier_error';out['warning']=type(ex).__name__
    out['seconds']=round(time.time()-started,2);out['completed_unix']=time.time()
    return out

async def process_pending():
    async with connection() as c:
        await ensure_schema(c)
        await c.execute("UPDATE recovery_assessment_requests SET status='pending',started_at=NULL WHERE status='running' AND started_at < now()-interval '10 minutes'")
        req=await c.fetchrow("""UPDATE recovery_assessment_requests SET status='running',started_at=now()
          WHERE id=(SELECT id FROM recovery_assessment_requests WHERE status='pending' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED)
          RETURNING id,intent_id,shadow,assessment_kind,evidence""")
    if not req:return None
    evidence=_obj(req['evidence'])
    out=await review(evidence,bool(req['shadow']))
    async with connection() as c:
        await c.execute("UPDATE recovery_assessment_requests SET status='complete',result=$2::jsonb,completed_at=now() WHERE id=$1",req['id'],json.dumps(out))
    return {'request_id':int(req['id']),'intent_id':int(req['intent_id']),'assessment_kind':req['assessment_kind'],**out}

async def latest(intent_id:int):
    async with connection() as c:
        await ensure_schema(c)
        r=await c.fetchrow("SELECT id,status,evidence,result,requested_at,completed_at FROM recovery_assessment_requests WHERE intent_id=$1 ORDER BY id DESC LIMIT 1",intent_id)
        return None if not r else dict(r)

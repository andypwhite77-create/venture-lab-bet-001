"""Swarm Queen: read-only executive intelligence over isolated strategy colonies.
She monitors, synthesises and recommends; she never trades or rewrites colony genetics.
"""
import json, os, time, httpx
from db import connection

MODEL=os.getenv('SWARM_QUEEN_MODEL','qwen3:4b')
OLLAMA=os.getenv('OLLAMA_URL','http://127.0.0.1:11434/api/generate')
FAMILIES=('reversal','momentum','order_flow','wallet_convergence')

async def ensure_schema(c):
    await c.execute('''CREATE TABLE IF NOT EXISTS swarm_queen_journal(
      id BIGSERIAL PRIMARY KEY, observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      model TEXT NOT NULL, status TEXT NOT NULL, briefing JSONB NOT NULL,
      input_snapshot JSONB NOT NULL)''')

async def evidence(c):
    roster=[]
    rr=await c.fetchrow("SELECT run_id,stage_size,stage_index,status FROM reversal_tournament_runs ORDER BY created_at DESC LIMIT 1")
    if rr:
        x=await c.fetchrow("SELECT count(*) FILTER(WHERE active) active,count(*) FILTER(WHERE active AND baseline) controls,count(*) FILTER(WHERE active AND NOT baseline AND cohort='historical_qualified') elites FROM reversal_tournament_ants WHERE run_id=$1",rr['run_id'])
        roster.append({'family':'reversal',**dict(x),'stage':rr['stage_index'],'status':rr['status']})
    for r in await c.fetch("SELECT DISTINCT ON(family) run_id,family,stage_index,status FROM family_tournament_runs ORDER BY family,created_at DESC"):
        x=await c.fetchrow("SELECT count(*) FILTER(WHERE active) active,count(*) FILTER(WHERE active AND baseline) controls,count(*) FILTER(WHERE active AND NOT baseline AND cohort='historical_qualified') elites FROM family_tournament_ants WHERE run_id=$1",r['run_id'])
        roster.append({'family':r['family'],**dict(x),'stage':r['stage_index'],'status':r['status']})
    perf=[dict(x) for x in await c.fetch('''SELECT quote->'attribution'->>'family' family,count(*) trades,count(*) FILTER(WHERE net_pnl>0) wins,coalesce(sum(net_pnl),0) net,avg(net_pnl) FILTER(WHERE net_pnl IS NOT NULL) avg_net FROM colony_execution_ledger WHERE run_id='colony-native-v3-holdaware' GROUP BY 1''')]
    queue=[dict(x) for x in await c.fetch("SELECT family,count(*) waiting,max(historical_score) best FROM evolution_candidate_queue WHERE status='ready' GROUP BY family")]
    providers=[dict(x) for x in await c.fetch("SELECT DISTINCT ON(provider) provider,ok,error,observed_at FROM colony_provider_health ORDER BY provider,observed_at DESC")]
    recent=[dict(x) for x in await c.fetch("SELECT event_type,payload,created_at FROM colony_events ORDER BY id DESC LIMIT 12")]
    return {'roster':roster,'performance':perf,'challenger_queue':queue,'providers':providers,'recent_events':recent,
            'constitution':{'authority':'advisory_only','real_money':False,'may_rewrite_genetics':False,'may_relax_evidence_gates':False,
                            'shared_data':True,'isolated_colony_genetics':True}}

def prompt(e):
    return '''You are Swarm Queen, executive monitor for four isolated trading research colonies: Reversal, Momentum, Order Flow, Wallet Convergence. You are Grace's point of contact. Summarise only material evidence. Compare colonies, detect system faults, regime deterioration, correlation/corroboration, and recommend where research attention belongs. Never claim authority to trade real money, change evidence gates, or edit colony genetics. A colony may trade the same mint differently; shared observations are evidence, not genetic leakage. Return JSON only with keys status (healthy|warning|critical), summary, material_changes (array), colony_notes (object keyed by family), recommendations (array). Evidence: '''+json.dumps(e,default=str,separators=(',',':'))[:12000]

async def wake():
    async with connection() as c:
        await ensure_schema(c); e=await evidence(c)
    schema={'type':'object','properties':{'status':{'type':'string','enum':['healthy','warning','critical']},'summary':{'type':'string'},'material_changes':{'type':'array','items':{'type':'string'}},'colony_notes':{'type':'object'},'recommendations':{'type':'array','items':{'type':'string'}}},'required':['status','summary','material_changes','colony_notes','recommendations'],'additionalProperties':False}
    started=time.time()
    try:
        async with httpx.AsyncClient(timeout=180) as h:
            r=await h.post(OLLAMA,json={'model':MODEL,'prompt':prompt(e),'stream':False,'format':schema,'think':False,'options':{'num_ctx':4096,'num_predict':650,'temperature':0.1}}); r.raise_for_status(); b=json.loads(r.json()['response'])
        state='ok'
    except Exception as ex:
        b={'status':'warning','summary':'Swarm Queen inference unavailable','material_changes':[str(ex)[:180]],'colony_notes':{},'recommendations':['Continue deterministic monitoring; no authority changes.']}; state='inference_error'
    async with connection() as c:
        await ensure_schema(c); await c.execute("INSERT INTO swarm_queen_journal(model,status,briefing,input_snapshot) VALUES($1,$2,$3::jsonb,$4::jsonb)",MODEL,state,json.dumps(b),json.dumps(e,default=str))
    return {'model':MODEL,'seconds':round(time.time()-started,2),'briefing':b}

async def latest():
    async with connection() as c:
        await ensure_schema(c); r=await c.fetchrow("SELECT observed_at,model,status,briefing FROM swarm_queen_journal ORDER BY id DESC LIMIT 1")
        return dict(r) if r else None

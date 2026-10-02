import asyncio, base64, hashlib, hmac, json, os, secrets, time, urllib.request
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from db import connection, init_db
from colony.live_registry import ensure_schema as ensure_live_schema, sync_spartan_passers, treasury_snapshot, update_treasury_policy, set_live_authority
from colony.eve_reference_paper import stats as eve_reference_stats
from colony.champion_league import ensure_schema as ensure_champion_schema
from colony.qualification_corpus import ensure_schema as ensure_corpus_schema, snapshot as qualification_corpus_snapshot
from colony.queen_roles import snapshot as queen_role_snapshot
from colony.admin_auth import ensure_schema as ensure_auth_schema, current_password_hash, verify_password as verify_admin_password, reset_password_with_token

app = FastAPI(title="Venture Lab Control Plane", docs_url=None, redoc_url=None, openapi_url=None)
USER = os.getenv("ADMIN_USERNAME", "admin")
PASS = os.getenv("ADMIN_PASSWORD_SCRYPT", "")
SECRET = os.getenv("ADMIN_SESSION_SECRET", "").encode()
RPC = os.getenv("SOLANA_SECONDARY_RPC_URL", "https://api.mainnet-beta.solana.com")
QUEEN_SURVIVAL='/run/queen/queen_survival_state.json'
QUEEN_MEMORY='/run/queen/queen_memory.json'

def read_json(path):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return {}

MODES = {"disabled","research","paper","shadow","live-ready","live"}
LOGIN_FAILS = {}
RECOVERY_FAILS = {}
AUTH_EPOCH = 1

class Login(BaseModel): username:str; password:str
class RecoverIn(BaseModel): username:str; recovery_code:str; new_password:str
class WalletIn(BaseModel): label:str; address:str
class ComponentIn(BaseModel): mode:str; wallet_id:int|None=None; max_trade_gbp:float|None=None; floor_gbp:float|None=None
class AuthorityIn(BaseModel): enabled:bool
class EliteModeIn(BaseModel): mode:str
class TreasuryIn(BaseModel):
    enabled:bool=False
    auto_withdraw_enabled:bool=False
    personal_wallet_id:int|None=None
    withdraw_pct:float=0
    reinvest_pct:float=100
    withdraw_trigger_gbp:float=20
    reinvest_trigger_gbp:float=5
    min_operating_bankroll_gbp:float=25
    max_family_exposure_pct:float=40
    max_ant_stake_gbp:float=25

def now(): return datetime.now(timezone.utc)
def make_session():
    exp=str(int(time.time())+8*3600); nonce=secrets.token_hex(16); raw=f"{USER}|{exp}|{nonce}|{AUTH_EPOCH}"
    sig=hmac.new(SECRET,raw.encode(),hashlib.sha256).hexdigest(); return raw+"|"+sig

def parse_session(value):
    try:
        user,exp,nonce,epoch,sig=value.split("|",4); raw=f"{user}|{exp}|{nonce}|{epoch}"
        good=hmac.compare_digest(sig,hmac.new(SECRET,raw.encode(),hashlib.sha256).hexdigest())
        if not good or user!=USER or int(exp)<time.time() or int(epoch)!=AUTH_EPOCH:return None
        return {"user":user,"exp":int(exp),"nonce":nonce,"raw":raw}
    except Exception:return None

def auth(request):
    s=parse_session(request.cookies.get("vl_admin",""))
    if not s: raise HTTPException(401,"login_required")
    return s

def csrf_for(s): return hmac.new(SECRET,(s["raw"]+"|csrf").encode(),hashlib.sha256).hexdigest()
def require_csrf(request,s):
    if not hmac.compare_digest(request.headers.get("x-csrf-token",""),csrf_for(s)): raise HTTPException(403,"csrf")

ALPH='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def b58decode(txt):
    n=0
    for ch in txt:
        if ch not in ALPH: raise ValueError()
        n=n*58+ALPH.index(ch)
    raw=n.to_bytes((n.bit_length()+7)//8,'big') if n else b''
    return b'\0'*(len(txt)-len(txt.lstrip('1')))+raw

def valid_solana(addr):
    try: return len(addr)>=32 and len(b58decode(addr))==32
    except Exception: return False
async def ensure_schema():
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS admin_wallets(
          id BIGSERIAL PRIMARY KEY,label TEXT NOT NULL,address TEXT UNIQUE NOT NULL,chain TEXT NOT NULL DEFAULT 'solana',
          mode TEXT NOT NULL DEFAULT 'disabled',enabled BOOLEAN NOT NULL DEFAULT true,
          max_trade_gbp DOUBLE PRECISION,floor_gbp DOUBLE PRECISION,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
        CREATE TABLE IF NOT EXISTS admin_components(
          id BIGSERIAL PRIMARY KEY,name TEXT UNIQUE NOT NULL,service_name TEXT,mode TEXT NOT NULL DEFAULT 'research',
          wallet_id BIGINT REFERENCES admin_wallets(id) ON DELETE SET NULL,max_trade_gbp DOUBLE PRECISION,
          floor_gbp DOUBLE PRECISION,live_allowed BOOLEAN NOT NULL DEFAULT false,updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
        CREATE TABLE IF NOT EXISTS admin_control(
          id INT PRIMARY KEY CHECK(id=1),global_live_stop BOOLEAN NOT NULL DEFAULT true,updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
        INSERT INTO admin_control(id) VALUES(1) ON CONFLICT DO NOTHING;
        CREATE TABLE IF NOT EXISTS elite_control(
          id INT PRIMARY KEY CHECK(id=1),desired_mode TEXT NOT NULL DEFAULT 'off' CHECK(desired_mode IN ('off','canary','live')),
          execution_bridge_connected BOOLEAN NOT NULL DEFAULT false,updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
        INSERT INTO elite_control(id) VALUES(1) ON CONFLICT DO NOTHING;
        CREATE TABLE IF NOT EXISTS admin_audit(
          id BIGSERIAL PRIMARY KEY,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),actor TEXT NOT NULL,
          action TEXT NOT NULL,target TEXT,detail JSONB NOT NULL DEFAULT '{}');''')
        defaults=[('queen_survival','queen-survival','research'),('swarm_queen','swarm-queen','research'),
                  ('reversal_tournament','colony','research'),('paper_pipeline','paper','paper'),
                  ('reversal_canary','canary-executor','shadow')]
        for name,svc,mode in defaults:
            await c.execute('INSERT INTO admin_components(name,service_name,mode) VALUES($1,$2,$3) ON CONFLICT(name) DO NOTHING',name,svc,mode)
        addr='j4nCnM29iyZx9n8oKHXBk8HNJESZb5yaBsA1VkvtkGZ'
        wid=await c.fetchval("INSERT INTO admin_wallets(label,address,mode,max_trade_gbp,floor_gbp) VALUES('Reversal Canary',$1,'shadow',1,4) ON CONFLICT(address) DO UPDATE SET address=EXCLUDED.address RETURNING id",addr)
        await c.execute("UPDATE admin_components SET wallet_id=COALESCE(wallet_id,$1),max_trade_gbp=COALESCE(max_trade_gbp,1),floor_gbp=COALESCE(floor_gbp,4) WHERE name='reversal_canary'",wid)

async def audit(action,target=None,detail=None):
    async with connection() as c:
        await c.execute('INSERT INTO admin_audit(actor,action,target,detail) VALUES($1,$2,$3,$4)',USER,action,target,json.dumps(detail or {}))
async def sol_balance(address):
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':'getBalance','params':[address,{'commitment':'confirmed'}]}).encode()
    req=urllib.request.Request(RPC,data=body,headers={'content-type':'application/json'})
    def go():
        with urllib.request.urlopen(req,timeout=8) as r: return json.load(r)
    data=await asyncio.to_thread(go)
    if data.get('error'): raise RuntimeError('rpc_error')
    return data['result']['value']/1_000_000_000

@app.on_event('startup')
async def startup():
    global AUTH_EPOCH
    if not PASS or len(SECRET)<32: raise RuntimeError('admin_credentials_not_configured')
    await init_db(); await ensure_schema()
    async with connection() as c:
        await ensure_auth_schema(c)
        AUTH_EPOCH=int((await c.fetchrow('SELECT auth_epoch FROM admin_auth_state WHERE id=1'))['auth_epoch'])
        await ensure_live_schema(c); await sync_spartan_passers(c)
        await ensure_champion_schema(c); await ensure_corpus_schema(c)

@app.post('/admin/api/login')
async def login(data:Login,request:Request,response:Response):
    ip=request.client.host if request.client else 'unknown'; cutoff=time.time()-600
    LOGIN_FAILS[ip]=[t for t in LOGIN_FAILS.get(ip,[]) if t>cutoff]
    if len(LOGIN_FAILS[ip])>=5: raise HTTPException(429,'try_later')
    async with connection() as c:
        encoded=await current_password_hash(c,PASS)
    if data.username!=USER or not verify_admin_password(encoded,data.password):
        LOGIN_FAILS[ip].append(time.time()); await asyncio.sleep(.4); raise HTTPException(401,'invalid_login')
    LOGIN_FAILS.pop(ip,None); token=make_session()
    response.set_cookie('vl_admin',token,max_age=8*3600,httponly=True,secure=True,samesite='strict',path='/admin')
    await audit('login'); return {'ok':True}

@app.post('/admin/api/recover')
async def recover(data:RecoverIn,request:Request,response:Response):
    global AUTH_EPOCH
    ip=request.client.host if request.client else 'unknown'; cutoff=time.time()-600
    RECOVERY_FAILS[ip]=[t for t in RECOVERY_FAILS.get(ip,[]) if t>cutoff]
    if len(RECOVERY_FAILS[ip])>=5: raise HTTPException(429,'try_later')
    if data.username!=USER:
        RECOVERY_FAILS[ip].append(time.time()); await asyncio.sleep(.5); raise HTTPException(401,'invalid_recovery')
    async with connection() as c:
        result=await reset_password_with_token(c,data.recovery_code,data.new_password)
    if not result.get('ok'):
        RECOVERY_FAILS[ip].append(time.time()); await asyncio.sleep(.5); raise HTTPException(401,result.get('reason','invalid_recovery'))
    AUTH_EPOCH=int(result['auth_epoch']); RECOVERY_FAILS.pop(ip,None); LOGIN_FAILS.pop(ip,None)
    response.delete_cookie('vl_admin',path='/admin')
    await audit('password_recovered','admin',{'sessions_invalidated':True})
    return {'ok':True,'sessions_invalidated':True}

@app.post('/admin/api/logout')
async def logout(request:Request,response:Response):
    s=auth(request); require_csrf(request,s); response.delete_cookie('vl_admin',path='/admin'); await audit('logout'); return {'ok':True}

@app.get('/admin/api/me')
async def me(request:Request):
    s=auth(request); return {'user':s['user'],'csrf':csrf_for(s),'expires':s['exp']}
@app.get('/admin/api/state')
async def api_state(request:Request):
    auth(request)
    async with connection() as c:
        wallets=[dict(r) for r in await c.fetch('SELECT * FROM admin_wallets ORDER BY id')]
        components=[dict(r) for r in await c.fetch('SELECT * FROM admin_components ORDER BY id')]
        control=dict(await c.fetchrow('SELECT * FROM admin_control WHERE id=1'))
        elite_control=dict(await c.fetchrow('SELECT * FROM elite_control WHERE id=1'))
        await ensure_champion_schema(c); await ensure_corpus_schema(c)
        elite_roster=[dict(r) for r in await c.fetch("SELECT elite_slot,genome_id,family,source,arena_score,forward_score,total_score,arena_stats,forward_stats,promoted_at FROM champion_league WHERE pool='elite' ORDER BY elite_slot")]
        qualification_top=[dict(r) for r in await c.fetch("SELECT qualification_rank,genome_id,family,source,arena_score,forward_score,total_score,arena_stats,forward_stats FROM champion_league WHERE pool='qualification' ORDER BY qualification_rank NULLS LAST,total_score DESC NULLS LAST LIMIT 10")]
        qualification_corpus=await qualification_corpus_snapshot(c)
        canary=await c.fetchrow('SELECT armed,stopped,since,heartbeat,problem FROM canary_control WHERE id=1')
        canary_counts=[dict(r) for r in await c.fetch("SELECT status,count(*)::int count FROM canary_trade_intents GROUP BY status ORDER BY status")]
        latest_intent=await c.fetchrow("SELECT candidate_id,status,vote_fraction,observed_at,reason FROM canary_trade_intents ORDER BY id DESC LIMIT 1")
        await ensure_live_schema(c); await sync_spartan_passers(c)
        live_ants=[dict(r) for r in await c.fetch('''SELECT id,genome_id,family,species,lineage,source,promotion_stage,spartan_passed,canary_profile,canary_passed,live_authorized,evidence_version,updated_at FROM live_ant_registry WHERE live_candidate=true ORDER BY family,species,genome_id''')]
        paper_stats={x['genome_id']:x for x in await eve_reference_stats(c)}
        for a in live_ants:a['paper']=paper_stats.get(a['genome_id'])
        treasury=await treasury_snapshot(c)
        audit_rows=[dict(r) for r in await c.fetch('SELECT created_at,action,target,detail FROM admin_audit ORDER BY id DESC LIMIT 25')]
        swarm=None
        if await c.fetchval("SELECT to_regclass('public.swarm_queen_journal') IS NOT NULL"):
            sr=await c.fetchrow("SELECT observed_at,model,status,briefing FROM swarm_queen_journal ORDER BY id DESC LIMIT 1")
            swarm=dict(sr) if sr else None
    for w in wallets:
        try: w['balance_sol']=await sol_balance(w['address'])
        except Exception: w['balance_sol']=None
    qsurv=read_json(QUEEN_SURVIVAL); qmem=read_json(QUEEN_MEMORY)
    roles=queen_role_snapshot()
    queen={'campaign':qsurv.get('campaign'),'tested':qsurv.get('tested'),'finalists':qsurv.get('finalists'),'holdout_positive':qsurv.get('holdout_positive'),'spartan_survivors':qsurv.get('spartan_survivors'),'memory_campaigns':qmem.get('campaigns'),'preferred_features':(qmem.get('preferred_features') or [])[:6],'role':roles['breeding_queen']}
    return {'wallets':wallets,'components':components,'control':control,'elite_control':elite_control,'elite_roster':elite_roster,'qualification_top':qualification_top,'qualification_corpus':qualification_corpus,'canary':dict(canary) if canary else None,'canary_counts':canary_counts,'latest_intent':dict(latest_intent) if latest_intent else None,'queen':queen,'swarm_queen':swarm,'queen_roles':roles,'live_ants':live_ants,'treasury':treasury,'audit':audit_rows}

@app.post('/admin/api/wallets')
async def add_wallet(data:WalletIn,request:Request):
    s=auth(request); require_csrf(request,s)
    label=data.label.strip()[:80]; address=data.address.strip()
    if not label or not valid_solana(address): raise HTTPException(400,'invalid_wallet')
    async with connection() as c:
        try: row=await c.fetchrow('INSERT INTO admin_wallets(label,address) VALUES($1,$2) RETURNING id',label,address)
        except Exception: raise HTTPException(409,'wallet_exists')
    await audit('wallet_add',address,{'label':label}); return {'ok':True,'id':row['id']}

@app.delete('/admin/api/wallets/{wallet_id}')
async def delete_wallet(wallet_id:int,request:Request):
    s=auth(request); require_csrf(request,s)
    async with connection() as c:
        if await c.fetchval('SELECT 1 FROM admin_components WHERE wallet_id=$1',wallet_id): raise HTTPException(409,'wallet_in_use')
        addr=await c.fetchval('DELETE FROM admin_wallets WHERE id=$1 RETURNING address',wallet_id)
    if not addr: raise HTTPException(404,'wallet_not_found')
    await audit('wallet_remove',addr); return {'ok':True}
@app.post('/admin/api/components/{component_id}')
async def update_component(component_id:int,data:ComponentIn,request:Request):
    s=auth(request); require_csrf(request,s)
    if data.mode not in MODES: raise HTTPException(400,'bad_mode')
    if data.max_trade_gbp is not None and not 0<=data.max_trade_gbp<=10000: raise HTTPException(400,'bad_limit')
    if data.floor_gbp is not None and not 0<=data.floor_gbp<=1000000: raise HTTPException(400,'bad_floor')
    async with connection() as c:
        row=await c.fetchrow('''UPDATE admin_components SET mode=$2,wallet_id=$3,max_trade_gbp=$4,floor_gbp=$5,updated_at=now()
          WHERE id=$1 RETURNING name''',component_id,data.mode,data.wallet_id,data.max_trade_gbp,data.floor_gbp)
    if not row: raise HTTPException(404,'component_not_found')
    await audit('component_update',row['name'],data.model_dump()); return {'ok':True}

@app.post('/admin/api/live-ants/{ant_id}/authority')
async def live_ant_authority(ant_id:int,data:AuthorityIn,request:Request):
    s=auth(request); require_csrf(request,s)
    async with connection() as c:
        if data.enabled:
            control=await c.fetchrow('SELECT global_live_stop FROM admin_control WHERE id=1')
            if control and control['global_live_stop']:
                raise HTTPException(409,'global_live_stop_active')
        try: row=await set_live_authority(c,ant_id,data.enabled)
        except ValueError as e: raise HTTPException(409,str(e))
    await audit('live_ant_authority',str(ant_id),row)
    return {'ok':True,**row}

@app.post('/admin/api/elite-mode')
async def set_elite_mode(data:EliteModeIn,request:Request):
    s=auth(request); require_csrf(request,s)
    mode=data.mode.strip().lower()
    if mode not in {'off','canary','live'}: raise HTTPException(400,'bad_elite_mode')
    async with connection() as c:
        row=await c.fetchrow('SELECT global_live_stop FROM admin_control WHERE id=1')
        ctl=await c.fetchrow('SELECT execution_bridge_connected FROM elite_control WHERE id=1')
        if mode!='off' and row and row['global_live_stop']: raise HTTPException(409,'global_live_stop_active')
        if mode=='live' and not bool(ctl['execution_bridge_connected']): raise HTTPException(409,'elite_execution_bridge_not_connected')
        await c.execute('UPDATE elite_control SET desired_mode=$1,updated_at=now() WHERE id=1',mode)
    await audit('elite_mode_request','elite',{'mode':mode})
    return {'ok':True,'desired_mode':mode,'execution_bridge_connected':bool(ctl['execution_bridge_connected'])}

@app.post('/admin/api/treasury-policy')
async def set_treasury_policy(data:TreasuryIn,request:Request):
    s=auth(request); require_csrf(request,s)
    if data.auto_withdraw_enabled and (not data.enabled or data.personal_wallet_id is None):
        raise HTTPException(400,'auto_withdraw_requires_enabled_policy_and_wallet')
    async with connection() as c:
        if data.personal_wallet_id is not None and not await c.fetchval('SELECT 1 FROM admin_wallets WHERE id=$1',data.personal_wallet_id):
            raise HTTPException(400,'treasury_wallet_not_found')
        try: row=await update_treasury_policy(c,data.model_dump())
        except ValueError as e: raise HTTPException(400,str(e))
    await audit('treasury_policy_update','treasury',data.model_dump())
    return {'ok':True,'policy':row}

@app.post('/admin/api/global-stop')
async def global_stop(request:Request):
    s=auth(request); require_csrf(request,s)
    async with connection() as c:
        async with c.transaction():
            await c.execute('UPDATE admin_control SET global_live_stop=true,updated_at=now() WHERE id=1')
            await c.execute("UPDATE elite_control SET desired_mode='off',updated_at=now() WHERE id=1")
            if await c.fetchval("SELECT to_regclass('public.canary_control') IS NOT NULL"):
                await c.execute("UPDATE canary_control SET armed=false,stopped=true,since=now(),problem='admin_global_stop' WHERE id=1")
    await audit('global_live_stop'); return {'ok':True}

@app.post('/admin/api/global-resume')
async def global_resume(request:Request):
    s=auth(request); require_csrf(request,s)
    async with connection() as c: await c.execute('UPDATE admin_control SET global_live_stop=false,updated_at=now() WHERE id=1')
    await audit('global_live_resume'); return {'ok':True}
PAGE='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cobalt Labs | Network Control</title><style>
:root{--bg:#020b16;--panel:#07182a;--line:#173a59;--blue:#1677ff;--text:#f4f8fc;--muted:#8fa9c2;--good:#42d392;--bad:#ff667a}*{box-sizing:border-box}body{font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;background:radial-gradient(circle at 25% -10%,#0a3157 0,#03101f 34%,#020914 72%);color:var(--text);margin:0;min-height:100vh}body:before{content:"";position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(31,116,194,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(31,116,194,.04) 1px,transparent 1px);background-size:48px 48px}main{max-width:1240px;margin:0 auto;padding:26px}.brandbar{display:flex;align-items:center;justify-content:space-between;padding:18px 0 8px;border-bottom:1px solid #10304c;margin-bottom:22px}.brand{font-size:22px;letter-spacing:7px}.brand b{color:var(--blue);font-size:12px;vertical-align:sub;letter-spacing:0}.brand small{font-size:9px;letter-spacing:6px;color:#adc2d6}.tag{font-size:10px;letter-spacing:1.5px;color:#8fb4d7;border:1px solid #195c96;border-radius:6px;padding:8px 10px}.hero{margin:16px 0 20px}.hero .k{color:var(--blue);font-size:10px;letter-spacing:3px;font-weight:700}.hero h1{font-size:34px;letter-spacing:-1px;margin:6px 0}.hero h1 span{color:var(--blue)}.card{background:linear-gradient(180deg,rgba(8,28,47,.97),rgba(4,17,30,.97));border:1px solid var(--line);border-radius:10px;padding:18px;margin:12px 0;box-shadow:0 16px 42px rgba(0,0,0,.18)}.row{display:flex;gap:12px;flex-wrap:wrap}.row>.card{flex:1;min-width:260px}button,input,select{background:#06111e;color:var(--text);border:1px solid #21486a;border-radius:6px;padding:9px}button{cursor:pointer}.danger{border-color:#b94c5d;color:#ffd6dc}.ok{color:var(--good)}.bad{color:var(--bad)}.muted{color:var(--muted)}.hidden{display:none}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:9px;border-bottom:1px solid #14314d;text-align:left}th{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#88a6c1}code{font-size:11px;color:#c3ddf4}h3{font-size:13px;letter-spacing:.7px;text-transform:uppercase}.metric{font-size:26px;font-weight:700}.pill{display:inline-block;border:1px solid #21547e;background:#08233d;border-radius:999px;padding:4px 8px;font-size:10px;margin:2px}@media(max-width:700px){body{font-size:15px}main{padding:10px}.brandbar{padding:12px 2px;margin-bottom:14px}.brand{font-size:18px;letter-spacing:4px}.brand small{letter-spacing:3px}.tag{display:none}.hero{margin:10px 2px 14px}.hero .k{font-size:9px;letter-spacing:2px}.hero h1{font-size:27px;line-height:1.05;margin:5px 0}.row{display:grid;grid-template-columns:1fr;gap:8px}.row>.card{min-width:0;margin:0}.card{padding:14px;margin:8px 0;border-radius:9px}h3{font-size:12px;margin-top:0}.metric{font-size:24px}button,input,select{min-height:44px;font-size:16px}#login input,#login button,#wlabel,#waddr{width:100%;margin:5px 0}#login{margin-top:12px}.tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -4px}table{min-width:680px}#auditTable{min-width:520px}.mobileActions button{width:100%;margin:4px 0}.pill{font-size:9px;max-width:100%;overflow:hidden;text-overflow:ellipsis}.muted{line-height:1.4}code{font-size:10px;word-break:break-all}.walletaddr{max-width:180px;overflow:hidden;text-overflow:ellipsis;display:block}.footer{font-size:9px;gap:8px;flex-direction:column} }@media(min-width:701px) and (max-width:1000px){main{padding:18px}.row>.card{min-width:220px}.brand{font-size:20px}.hero h1{font-size:31px}}</style></head><body><main>
<div class="brandbar"><div class="brand">C<b>27</b> COBALT <small>LABS</small></div><div class="tag">🔒 SECURE NETWORK CONTROL</div></div><div class="hero"><div class="k">COBALT LABS // VENTURE LAB</div><h1>NETWORK <span>CONTROL</span></h1><div class="muted">Research intelligence. Execution discipline. Capital protection.</div></div><div id="login" class="card"><h3>Admin login</h3><input id="user" value="admin" autocomplete="username"><input id="pass" type="password" autocomplete="current-password"><button onclick="login()">Sign in</button><div id="loginmsg" class="bad"></div></div>
<div id="app" class="hidden"><div class="row"><div class="card"><h3>Breeding Queen / Spartan</h3><div id="queen">Loading…</div></div><div class="card"><h3>Reversal canary</h3><div id="canary"></div></div><div class="card"><h3>Live safety</h3><div id="global"></div><br><div class="mobileActions"><button class="danger" onclick="post('/admin/api/global-stop')">GLOBAL LIVE STOP</button> <button onclick="post('/admin/api/global-resume')">Clear stop flag</button></div></div></div>
<div class="card"><h3>Wallet registry</h3><div class="muted">Public addresses only. Private keys are never stored here.</div><input id="wlabel" placeholder="Label"><input id="waddr" placeholder="Solana address" size="48"><button onclick="addWallet()">Add wallet</button><div class="tablewrap"><table><thead><tr><th>Label</th><th>Address</th><th>Balance</th><th>Mode</th><th></th></tr></thead><tbody id="wallets"></tbody></table></div></div>
<div class="card"><h3>Network components</h3><div class="tablewrap"><table><thead><tr><th>Component</th><th>Service</th><th>Mode</th><th>Wallet</th><th>Max £</th><th>Floor £</th><th></th></tr></thead><tbody id="components"></tbody></table></div></div>
<div class="card"><h3>Audit log</h3><div class="tablewrap"><table id="auditTable"><tbody id="audit"></tbody></table></div></div></div>
<script>let csrf='',state=null;const modes=['disabled','research','paper','shadow','live-ready','live'];
async function req(url,opt={}){opt.headers=Object.assign({'content-type':'application/json'},opt.headers||{});if(csrf)opt.headers['x-csrf-token']=csrf;let r=await fetch(url,opt);if(!r.ok)throw Error(await r.text());return r.json()}
async function login(){try{await req('/admin/api/login',{method:'POST',body:JSON.stringify({username:user.value,password:pass.value})});await boot()}catch(e){loginmsg.textContent='Login failed'}}
async function boot(){const loginBox=document.getElementById('login'),appBox=document.getElementById('app');try{let m=await req('/admin/api/me');csrf=m.csrf;loginBox.classList.add('hidden');appBox.classList.remove('hidden');await load()}catch(e){loginBox.classList.remove('hidden');appBox.classList.add('hidden');throw e}}
'''
PAGE+='''
async function load(){state=await req('/admin/api/state');global.innerHTML=state.control.global_live_stop?'<b class="bad">LIVE STOP ON</b>':'<b class="ok">Live stop clear</b>';canary.innerHTML=state.canary?`<div class="metric ${state.canary.armed?'bad':'blue'}">${state.canary.armed?'LIVE':(state.canary.stopped?'STOPPED':'DRY RUN')}</div><div class="muted">armed ${state.canary.armed} · stopped ${state.canary.stopped}</div><br>heartbeat: ${state.canary.heartbeat||'-'}<br>problem: ${state.canary.problem||'-'}<br><div style="margin-top:8px">${(state.canary_counts||[]).map(x=>`<span class="pill">${esc(x.status)} ${x.count}</span>`).join('')}</div>${state.latest_intent?`<br><span class="muted">latest #${state.latest_intent.candidate_id} · ${esc(state.latest_intent.status)} · ${(state.latest_intent.vote_fraction*100).toFixed(1)}%</span>`:''}`:'not configured';queen.innerHTML=state.queen?`<div class="metric">${state.queen.spartan_survivors||0}</div><div class="muted">Spartan survivors</div><br>campaign: <b>${state.queen.campaign??'-'}</b> · finalists: <b>${state.queen.finalists??'-'}</b><br>holdout positive: <b>${state.queen.holdout_positive??'-'}</b> · memory: <b>${state.queen.memory_campaigns??'-'}</b><br><div style="margin-top:8px">${(state.queen.preferred_features||[]).map(x=>`<span class="pill">${esc(x)}</span>`).join('')}</div>`:'unavailable';
wallets.innerHTML=state.wallets.map(w=>`<tr><td>${esc(w.label)}</td><td><code class="walletaddr">${esc(w.address)}</code></td><td>${w.balance_sol==null?'?':w.balance_sol.toFixed(6)+' SOL'}</td><td>${esc(w.mode)}</td><td><button onclick="delWallet(${w.id})">Remove</button></td></tr>`).join('');
let opts='<option value="">none</option>'+state.wallets.map(w=>`<option value="${w.id}">${esc(w.label)}</option>`).join('');
components.innerHTML=state.components.map(c=>`<tr><td>${esc(c.name)}</td><td>${esc(c.service_name||'')}</td><td><select id="m${c.id}">${modes.map(m=>`<option ${m==c.mode?'selected':''}>${m}</option>`).join('')}</select></td><td><select id="w${c.id}">${opts.replace('value="'+c.wallet_id+'"','value="'+c.wallet_id+'" selected')}</select></td><td><input id="x${c.id}" size="5" value="${c.max_trade_gbp??''}"></td><td><input id="f${c.id}" size="5" value="${c.floor_gbp??''}"></td><td><button onclick="saveComp(${c.id})">Save</button></td></tr>`).join('');
audit.innerHTML=state.audit.map(a=>`<tr><td>${a.created_at}</td><td>${esc(a.action)}</td><td>${esc(a.target||'')}</td></tr>`).join('')}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function post(url,body={}){try{await req(url,{method:'POST',body:JSON.stringify(body)});await load()}catch(e){alert(e.message)}}
async function addWallet(){await post('/admin/api/wallets',{label:wlabel.value,address:waddr.value});wlabel.value='';waddr.value=''}
async function delWallet(id){if(confirm('Remove this wallet from the registry?')){try{await req('/admin/api/wallets/'+id,{method:'DELETE'});await load()}catch(e){alert(e.message)}}}
async function saveComp(id){let wid=document.getElementById('w'+id).value;let max=document.getElementById('x'+id).value;let floor=document.getElementById('f'+id).value;await post('/admin/api/components/'+id,{mode:document.getElementById('m'+id).value,wallet_id:wid?Number(wid):null,max_trade_gbp:max===''?null:Number(max),floor_gbp:floor===''?null:Number(floor)})}
boot();setInterval(()=>{if(csrf)load()},15000)</script></main></body></html>'''

@app.get('/admin',response_class=HTMLResponse)
@app.get('/admin/',response_class=HTMLResponse)
async def admin_page():
    from pathlib import Path
    html=Path('admin_console.html').read_text()
    return HTMLResponse(html,headers={'Cache-Control':'no-store','X-Frame-Options':'DENY','Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'"})

@app.get('/admin/health')
async def admin_health(): return {'ok':True}

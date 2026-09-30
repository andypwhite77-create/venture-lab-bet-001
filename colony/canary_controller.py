"""Reversal canary controller.

Owns no trading authority. It observes the dedicated wallet, converts high-consensus
Reversal events into bounded trade intents, and refuses to arm if hard safety checks fail.
A separate user-controlled signer/execution layer is required to broadcast transactions.
"""
from __future__ import annotations
import asyncio,json,os,time,urllib.request
from pathlib import Path
from db import connection,init_db
from colony.paper_economics import sol_gbp_rate

LAMPORTS=1_000_000_000
ROOT=Path(__file__).resolve().parents[1]
ADDRESS_FILE=Path(os.getenv('CANARY_ADDRESS_FILE',ROOT/'secrets/reversal_canary_address.txt'))
MAX_TRADE_GBP=float(os.getenv('CANARY_MAX_TRADE_GBP','1.00'))
FLOOR_GBP=float(os.getenv('CANARY_FLOOR_GBP','4.00'))
MIN_VOTE_FRACTION=float(os.getenv('CANARY_MIN_VOTE_FRACTION','0.80'))
START_AFTER=int(os.getenv('CANARY_START_AFTER_CANDIDATE_ID','0'))
POLL_SECONDS=int(os.getenv('CANARY_POLL_SECONDS','20'))
RPC=os.getenv('SOLANA_SECONDARY_RPC_URL','https://api.mainnet-beta.solana.com').strip()
LIVE_ENABLED=os.getenv('CANARY_LIVE_ENABLED','0')=='1'
def wallet_address():
    return ADDRESS_FILE.read_text().strip()

def rpc_call(method,params):
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    req=urllib.request.Request(RPC,data=body,headers={'content-type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as r:
        data=json.loads(r.read())
    if data.get('error'):
        raise RuntimeError(f"rpc_error:{data['error']}")
    return data['result']

def wallet_balance_sol():
    result=rpc_call('getBalance',[wallet_address(),{'commitment':'confirmed'}])
    return float(result['value'])/LAMPORTS

async def ensure_schema():
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS canary_trade_intents(
          id BIGSERIAL PRIMARY KEY,candidate_id BIGINT UNIQUE NOT NULL,mint TEXT NOT NULL,
          observed_at TIMESTAMPTZ NOT NULL,votes INT NOT NULL,active_ants INT NOT NULL,
          vote_fraction DOUBLE PRECISION NOT NULL,requested_gbp DOUBLE PRECISION NOT NULL,
          requested_sol DOUBLE PRECISION NOT NULL,wallet_sol DOUBLE PRECISION NOT NULL,
          wallet_gbp DOUBLE PRECISION NOT NULL,status TEXT NOT NULL,reason TEXT,
          live_enabled BOOLEAN NOT NULL DEFAULT false,broadcast BOOLEAN NOT NULL DEFAULT false,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now())''')
async def latest_reversal_groups(limit=50):
    async with connection() as c:
        rows=await c.fetch('''WITH latest_run AS (
          SELECT run_id,last_candidate_id FROM reversal_tournament_runs ORDER BY created_at DESC LIMIT 1),
        aa AS (SELECT count(*)::int n FROM reversal_tournament_ants a JOIN latest_run r USING(run_id) WHERE a.active=true),
        x AS (SELECT e.candidate_id,e.mint,min(e.observed_at) observed_at,
          count(DISTINCT e.genome_id)::int votes
          FROM reversal_tournament_entries e JOIN latest_run r USING(run_id)
          JOIN reversal_tournament_ants a ON a.run_id=e.run_id AND a.genome_id=e.genome_id AND a.active=true
          WHERE e.candidate_id>$1 AND e.candidate_id <= r.last_candidate_id GROUP BY e.candidate_id,e.mint)
        SELECT x.*,aa.n active_ants FROM x CROSS JOIN aa
        ORDER BY x.candidate_id ASC LIMIT $2''',START_AFTER,limit)
    return [dict(r) for r in rows]

async def already_seen(candidate_id):
    async with connection() as c:
        return bool(await c.fetchval('SELECT 1 FROM canary_trade_intents WHERE candidate_id=$1',candidate_id))

async def record_intent(g,rate,balance_sol,status,reason):
    requested_gbp=min(MAX_TRADE_GBP,max(0.0,balance_sol*rate-FLOOR_GBP))
    requested_sol=requested_gbp/rate if rate>0 else 0.0
    frac=(g['votes']/g['active_ants']) if g['active_ants'] else 0.0
    async with connection() as c:
        await c.execute('''INSERT INTO canary_trade_intents(candidate_id,mint,observed_at,votes,active_ants,
          vote_fraction,requested_gbp,requested_sol,wallet_sol,wallet_gbp,status,reason,live_enabled,broadcast)
          VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,false) ON CONFLICT(candidate_id) DO NOTHING''',
          g['candidate_id'],g['mint'],g['observed_at'],g['votes'],g['active_ants'],frac,
          requested_gbp,requested_sol,balance_sol,balance_sol*rate,status,reason,LIVE_ENABLED)
async def process_once():
    await ensure_schema()
    rate,_=sol_gbp_rate()
    if not rate or rate<=0:
        return {'ok':False,'reason':'no_sol_gbp_rate'}
    try:
        balance_sol=wallet_balance_sol()
    except Exception as e:
        return {'ok':False,'reason':'wallet_rpc_failed','error':type(e).__name__}
    out=[]
    for g in await latest_reversal_groups():
        if await already_seen(g['candidate_id']):
            continue
        frac=(g['votes']/g['active_ants']) if g['active_ants'] else 0.0
        wallet_gbp=balance_sol*rate
        if wallet_gbp<=FLOOR_GBP:
            status,reason='rejected','floor_reached'
        elif frac<MIN_VOTE_FRACTION:
            status,reason='rejected','consensus_below_threshold'
        else:
            status,reason='ready','awaiting_user_controlled_execution_layer'
        await record_intent(g,rate,balance_sol,status,reason)
        out.append({'candidate_id':g['candidate_id'],'mint':g['mint'],'votes':g['votes'],
                    'active_ants':g['active_ants'],'vote_fraction':frac,'status':status,'reason':reason})
    return {'ok':True,'wallet':wallet_address(),'balance_sol':balance_sol,'balance_gbp':balance_sol*rate,
            'rate_gbp_per_sol':rate,'live_enabled':LIVE_ENABLED,'broadcast_capability':False,
            'max_trade_gbp':MAX_TRADE_GBP,'floor_gbp':FLOOR_GBP,'new_intents':out}

async def main():
    await init_db()
    while True:
        try:
            print(json.dumps(await process_once(),default=str),flush=True)
        except Exception as e:
            print(json.dumps({'ok':False,'error':type(e).__name__,'detail':str(e)[:200]}),flush=True)
        await asyncio.sleep(POLL_SECONDS)

if __name__=='__main__':
    asyncio.run(main())

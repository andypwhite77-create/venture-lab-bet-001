"""Isolated, fail-closed canary execution. Never retry an uncertain submission."""
import asyncio
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from db import connection, init_db
from colony.canary_controller import ensure_schema as controller_schema, rpc_call, wallet_address, wallet_balance_sol
from colony.paper_economics import sol_gbp_rate

EXPECTED='j4nCnM29iyZx9n8oKHXBk8HNJESZb5yaBsA1VkvtkGZ'
SOL='So11111111111111111111111111111111111111112'
LOCK=84619320
RESERVE_SOL=0.003 # rent + bounded network/priority fees, including exit
RECOVERY_WINDOW_SECONDS=int(os.getenv('CANARY_RECOVERY_WINDOW_SECONDS','900'))
RECOVERY_RETRY_SECONDS=int(os.getenv('CANARY_RECOVERY_RETRY_SECONDS','15'))

async def schema():
    await controller_schema()
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS canary_control (
          id int PRIMARY KEY CHECK(id=1), armed boolean NOT NULL DEFAULT false,
          stopped boolean NOT NULL DEFAULT true, since timestamptz NOT NULL DEFAULT now(),
          heartbeat timestamptz, problem text);
        ALTER TABLE canary_control ADD COLUMN IF NOT EXISTS recovery_only boolean NOT NULL DEFAULT false;
        INSERT INTO canary_control(id) VALUES(1) ON CONFLICT DO NOTHING;
        ALTER TABLE canary_trade_intents ADD COLUMN IF NOT EXISTS execution jsonb NOT NULL DEFAULT '{}';
        ALTER TABLE canary_trade_intents ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
        CREATE UNIQUE INDEX IF NOT EXISTS canary_one_position ON canary_trade_intents ((1))
          WHERE status IN ('claimed','open','submitting_entry','submitting_exit','uncertain');''')

class QuoteValidationRejected(Exception):
    def __init__(self, code):
        self.code=str(code)
        super().__init__(self.code)

class GatewayPreBroadcastRejected(Exception):
    def __init__(self, code):
        self.code=str(code)
        super().__init__(self.code)

_PREBROADCAST_CODES={'SIMULATION_FAILED','SLIPPAGE_EXCEEDED','INSUFFICIENT_BALANCE','INVALID_PARAMS','NO_ROUTE_FOUND'}

def classify_gateway_http_error(status, body):
    try:
        payload=json.loads(body.decode() if isinstance(body,(bytes,bytearray)) else str(body))
    except Exception:
        payload={}
    code=str(payload.get('code') or '')
    if status==400 and code in _PREBROADCAST_CODES:
        return code
    # Older Gateway serializers may omit the structured code. Keep this fallback
    # deliberately narrow to failures proven to occur in pre-send simulation.
    msg=str(payload.get('message') or '').lower()
    if status==400 and 'slippage tolerance exceeded' in msg:
        return 'SLIPPAGE_EXCEEDED'
    if status==400 and 'transaction simulation failed' in msg:
        return 'SIMULATION_FAILED'
    return None

def gateway(path, payload=None):
    key=os.environ.get('HUMMINGBOT_GATEWAY_API_KEY','')
    if not key: raise ValueError('gateway_key_missing')
    req=urllib.request.Request('http://127.0.0.1:15888'+path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=90) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        body=e.read(65536)
        code=classify_gateway_http_error(e.code,body)
        if code: raise GatewayPreBroadcastRejected(code) from None
        raise

def positive(x):
    x=float(x)
    if not math.isfinite(x) or x<=0: raise ValueError('invalid_amount')
    return x

def validate_quote(q, token_in, token_out, amount):
    try:
        raw=q['quoteResponse']
        if not q.get('quoteId') or q['tokenIn']!=token_in or q['tokenOut']!=token_out:
            raise QuoteValidationRejected('quote_pair')
        if raw['inputMint']!=token_in or raw['outputMint']!=token_out or raw['swapMode']!='ExactIn':
            raise QuoteValidationRejected('quote_route')
        if not raw['routePlan'] or not all(x.get('swapInfo',{}).get('ammKey') for x in raw['routePlan']):
            raise QuoteValidationRejected('empty_route')
        if int(raw['slippageBps'])>100 or int(raw['slippageBps'])<0: raise QuoteValidationRejected('slippage')
        impact=float(q['priceImpactPct'])
        if not math.isfinite(impact) or abs(impact)>1: raise QuoteValidationRejected('price_impact')
        if abs(positive(q['amountIn'])-amount)>max(1e-9,amount*1e-7): raise QuoteValidationRejected('quote_size')
        out=positive(q['amountOut']); minimum=positive(q['minAmountOut'])
        if minimum<out*.989999 or minimum>out: raise QuoteValidationRejected('quote_minimum')
        if positive(q['maxAmountIn'])>amount*1.0000001: raise QuoteValidationRejected('quote_maximum')
        raw_out=int(raw['outAmount']); threshold=int(raw['otherAmountThreshold'])
        if raw_out<=0 or int(raw['inAmount'])<=0 or not max(1,raw_out*99//100)<=threshold<=raw_out:
            raise QuoteValidationRejected('raw_threshold')
        raw_impact=float(raw['priceImpactPct'])
        if not math.isfinite(raw_impact) or abs(raw_impact)>0.01: raise QuoteValidationRejected('raw_price_impact')
        return q
    except QuoteValidationRejected:
        raise
    except (KeyError, TypeError, ValueError, OverflowError):
        raise QuoteValidationRejected('malformed_quote') from None

def raw_quote(token_in,token_out,amount):
    params=dict(chainNetwork='solana-mainnet-beta',connector='jupiter',baseToken=token_in,
                quoteToken=token_out,amount=amount,side='SELL',slippagePct=1)
    return gateway('/trading/router/quote-swap?'+urllib.parse.urlencode(params))

def quote(token_in,token_out,amount):
    return validate_quote(raw_quote(token_in,token_out,amount),token_in,token_out,amount)

def entry_trade_basis_sol(data):
    # Strategy/recovery basis is the actual swap input, not the whole wallet delta.
    # The latter can include one-time ATA rent and network plumbing that should be
    # tracked separately as treasury cost rather than demanding a market rebound.
    if data.get('entry_trade_sol') is not None:
        return positive(data['entry_trade_sol'])
    q=data.get('entry_quote') or {}
    if q.get('amountIn') is not None:
        return positive(q['amountIn'])
    return positive(data['entry_spent_sol'])

def exit_pnl_sol(q,data):
    return positive(q['minAmountOut'])-entry_trade_basis_sol(data)

def recovery_should_exit(q,data,now=None):
    now=time.time() if now is None else float(now)
    pnl=exit_pnl_sol(q,data)
    if pnl>=0: return True,'break_even_or_better',pnl
    if now>=float(data['recovery_deadline']): return True,'deadline',pnl
    return False,'wait',pnl

def limits(row,rate,balance):
    if wallet_address()!=EXPECTED: raise ValueError('wallet_mismatch')
    positive(rate); positive(balance)
    if row['active_ants']<=0 or row['votes']<1 or row['votes']>row['active_ants']:
        raise ValueError('consensus')
    if not 0<row['vote_fraction']<=1:
        raise ValueError('consensus')
    if not row['hold_minutes'] or not 1<=row['hold_minutes']<=1440: raise ValueError('hold')
    if row['mint']==SOL: raise ValueError('native_mint')
    requested_sol=positive(row['requested_sol'])
    requested_gbp=positive(row['requested_gbp'])
    if requested_gbp>1.00000001: raise ValueError('trade_cap')
    # Intent sizing is only an upper bound. Reprice at execution-time FX so a
    # harmless SOL/GBP move cannot turn a <=£1 intent into a rejected >£1 trade.
    spendable_sol=max(0.0,balance-RESERVE_SOL)
    amount=positive(min(requested_sol, requested_gbp/rate, 1.0/rate, spendable_sol))
    if amount*rate>1.00000001: raise ValueError('trade_cap')
    if balance-amount<RESERVE_SOL-1e-12: raise ValueError('network_reserve')
    return amount

async def save(c,row,status,data,reason=None):
    await c.execute('UPDATE canary_trade_intents SET status=$2,execution=$3::jsonb,reason=$4,updated_at=now() WHERE id=$1',
                    row['id'],status,json.dumps(data),reason)

async def halt(c,reason):
    await c.execute('UPDATE canary_control SET armed=false,stopped=true,recovery_only=false,problem=$1 WHERE id=1',reason)

async def enter_recovery(c,row,data,reason,raw=None):
    now=time.time()
    data.setdefault('strategy_exit_at',data.get('exit_at'))
    data.setdefault('strategy_exit_observed_at',datetime.now(timezone.utc).isoformat())
    if raw is not None:
        data['strategy_exit_raw_quote']=raw
    data.setdefault('recovery_started_at',now)
    data.setdefault('recovery_deadline',now+RECOVERY_WINDOW_SECONDS)
    data['recovery_next_at']=now
    data['recovery_last_reason']=reason
    await save(c,row,'recovery',data,reason)

async def reconcile(c,row):
    data=json.loads(row['execution']); leg='exit' if row['status']=='submitting_exit' else data.get('pending_leg','entry')
    signature=data.get(leg+'_signature')
    # No signature means Gateway may have broadcast before the connection/process died.
    # There is deliberately no timeout/requeue path. Operator reconciliation is required.
    if not signature:
        await save(c,row,'uncertain',data,'submission_outcome_unknown'); await halt(c,'submission_outcome_unknown'); return
    result=await asyncio.to_thread(rpc_call,'getTransaction',[signature,{'encoding':'jsonParsed','maxSupportedTransactionVersion':0,'commitment':'finalized'}])
    if result is None: return
    meta=result['meta']
    keys=[x['pubkey'] if isinstance(x,dict) else x for x in result['transaction']['message']['accountKeys']]
    if EXPECTED not in keys: raise ValueError('transaction_wallet')
    if meta['err']:
        await save(c,row,'uncertain',data,'transaction_failed'); await halt(c,'transaction_failed'); return
    idx=keys.index(EXPECTED)
    def total(name):
        return sum(float(x['uiTokenAmount']['uiAmountString']) for x in meta.get(name,[]) if x.get('owner')==EXPECTED and x['mint']==row['mint'])
    delta=total('postTokenBalances')-total('preTokenBalances')
    if leg=='entry':
        if delta<=0: raise ValueError('missing_fill')
        data['tokens']=delta; data['exit_at']=time.time()+row['hold_minutes']*60
        data['entry_spent_sol']=(meta['preBalances'][idx]-meta['postBalances'][idx])/1e9
        await save(c,row,'open',data)
    else:
        if delta>=0 or abs(delta+data['tokens'])>max(1e-9,data['tokens']*1e-6): raise ValueError('exit_fill_mismatch')
        data['closed_at']=datetime.now(timezone.utc).isoformat()
        data['exit_received_sol']=(meta['postBalances'][idx]-meta['preBalances'][idx])/1e9
        data['realized_treasury_pnl_sol']=data['exit_received_sol']-float(data['entry_spent_sol'])
        data['realized_trade_pnl_sol']=data['exit_received_sol']-entry_trade_basis_sol(data)
        await save(c,row,'closed',data)

async def submit(c,row,data,q,leg):
    # Serialize stop/disarm against the commit-before-send boundary.
    async with c.transaction():
        control=await c.fetchrow('SELECT * FROM canary_control WHERE id=1 FOR UPDATE')
        permitted=(leg=='exit' and control['recovery_only']) or (control['armed'] and not control['recovery_only'])
        if not permitted or control['stopped']: return False
        data['pending_leg']=leg; data[leg+'_quote']=q; data[leg+'_submitted_at']=time.time()
        await save(c,row,'submitting_'+leg,data)
        await c.execute('UPDATE canary_trade_intents SET broadcast=true,live_enabled=true WHERE id=$1',row['id'])
    try:
        result=await asyncio.to_thread(gateway,'/trading/router/execute-quote',dict(chainNetwork='solana-mainnet-beta',connector='jupiter',walletAddress=EXPECTED,quoteId=q['quoteId']))
    except GatewayPreBroadcastRejected as e:
        data[leg+'_prebroadcast_rejection']=e.code
        if leg=='entry':
            await save(c,row,'rejected',data,'gateway_'+e.code.lower())
            # Gateway proved the transaction never reached the signing/send stage.
            # Reject this opportunity but keep a previously armed Canary live.
            await c.execute('UPDATE canary_trade_intents SET broadcast=false WHERE id=$1',row['id'])
            return False
        # The entry is already real. Treat an exit-side pre-broadcast failure as
        # recoverable inventory: no new entry can be claimed while this row remains
        # in recovery, and the exit controller will re-quote inside its bounded window.
        await enter_recovery(c,row,data,'recovery_gateway_'+e.code.lower())
        return False
    if result.get('signature'):
        data[leg+'_signature']=result['signature']; await save(c,row,'submitting_'+leg,data)
    return True

async def tick():
    async with connection() as c:
        if not await c.fetchval('SELECT pg_try_advisory_lock($1)',LOCK): return
        row=None
        try:
            await c.execute('UPDATE canary_control SET heartbeat=now() WHERE id=1')
            row=await c.fetchrow("""SELECT * FROM canary_trade_intents
              WHERE status IN ('claimed','open','recovery','submitting_entry','submitting_exit','uncertain')
              ORDER BY CASE status WHEN 'submitting_exit' THEN 0 WHEN 'uncertain' THEN 1 WHEN 'recovery' THEN 2 WHEN 'open' THEN 3 ELSE 4 END,id LIMIT 1""")
            if row and row['status'] in ('submitting_entry','submitting_exit','uncertain'):
                await reconcile(c,row); return
            control=await c.fetchrow('SELECT * FROM canary_control WHERE id=1')
            if control['stopped']: return
            live=control['armed']
            recovery_only=control['recovery_only']
            if not row and recovery_only:
                await halt(c,'recovery_complete'); return
            if not row:
                async with c.transaction():
                    row=await c.fetchrow("""UPDATE canary_trade_intents SET status='claimed',execution=jsonb_build_object('mode',$2::text,'eligible_since',$1::text),updated_at=now()
                      WHERE id=(SELECT id FROM canary_trade_intents WHERE status='ready' AND observed_at >= $1
                      AND observed_at > now()-interval '3 minutes' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING *""",control['since'],'live' if live else 'dry')
                if not row: return
            data=json.loads(row['execution'])
            if row['status'] in ('claimed','ready'):
                if (datetime.now(timezone.utc)-row['observed_at']).total_seconds()>180:
                    await save(c,row,'rejected',data,'stale'); return
                rate,source=await asyncio.to_thread(sol_gbp_rate)
                if source!='kraken_public': raise ValueError('fresh_fx_required')
                balance=await asyncio.to_thread(wallet_balance_sol)
                amount=limits(row,rate,balance)
                q=await asyncio.to_thread(quote,SOL,row['mint'],amount)
                # Quote latency cannot extend intent freshness.
                if (datetime.now(timezone.utc)-row['observed_at']).total_seconds()>180: raise ValueError('stale')
                balance=await asyncio.to_thread(wallet_balance_sol); limits(row,rate,balance)
                if data.get('mode')=='live' and not live: return
                data.setdefault('mode','live' if live else 'dry')
                data.update(entry_quote=q,rate=rate,entry_trade_sol=amount,entry_spent_sol=amount,tokens=float(q['minAmountOut']),exit_at=time.time()+row['hold_minutes']*60)
                if data['mode']=='live': await submit(c,row,data,q,'entry')
                else:
                    async with c.transaction():
                        current_control=await c.fetchrow('SELECT * FROM canary_control WHERE id=1 FOR UPDATE')
                        if current_control['stopped']: return
                        await save(c,row,'open',data,'simulated_entry')
            elif row['status']=='open' and time.time()>=data['exit_at']:
                raw=await asyncio.to_thread(raw_quote,row['mint'],SOL,data['tokens'])
                try:
                    q=validate_quote(raw,row['mint'],SOL,data['tokens'])
                except QuoteValidationRejected as e:
                    if data['mode']=='live':
                        await enter_recovery(c,row,data,'recovery_quote_'+e.code,raw); return
                    raise
                if data['mode']=='live':
                    data['strategy_exit_at']=data.get('exit_at')
                    data['strategy_exit_observed_at']=datetime.now(timezone.utc).isoformat()
                    data['strategy_exit_quote']=q
                    should_exit,why,pnl=recovery_should_exit(q,dict(data,recovery_deadline=time.time()+RECOVERY_WINDOW_SECONDS),time.time())
                    data['strategy_horizon_pnl_sol']=pnl
                    if should_exit:
                        if not (live or recovery_only): return
                        balance=await asyncio.to_thread(wallet_balance_sol)
                        if balance<RESERVE_SOL: raise ValueError('exit_fee_reserve')
                        await submit(c,row,data,q,'exit')
                    else:
                        await enter_recovery(c,row,data,'recovery_negative_horizon',raw)
                else:
                    data.update(exit_quote=q,closed_at=datetime.now(timezone.utc).isoformat(),simulated_pnl_sol=float(q['minAmountOut'])-data['entry_spent_sol'])
                    async with c.transaction():
                        current_control=await c.fetchrow('SELECT * FROM canary_control WHERE id=1 FOR UPDATE')
                        if current_control['stopped']: return
                        await save(c,row,'closed',data,'simulated_exit')
                        await halt(c,'dry_run_complete')
            elif row['status']=='recovery':
                if data.get('mode')!='live': raise ValueError('recovery_non_live')
                if not recovery_only and not live: return
                now=time.time()
                if now<float(data.get('recovery_next_at',0)): return
                try:
                    raw=await asyncio.to_thread(raw_quote,row['mint'],SOL,data['tokens'])
                    q=validate_quote(raw,row['mint'],SOL,data['tokens'])
                except QuoteValidationRejected as e:
                    data['recovery_last_reason']='recovery_quote_'+e.code
                    data['recovery_last_attempt_at']=now
                    data['recovery_next_at']=now+RECOVERY_RETRY_SECONDS
                    if now>=float(data['recovery_deadline']):
                        await save(c,row,'recovery',data,'recovery_deadline_no_safe_quote')
                        await halt(c,'recovery_deadline_no_safe_quote')
                    else:
                        await save(c,row,'recovery',data,data['recovery_last_reason'])
                    return
                should_exit,why,pnl=recovery_should_exit(q,data,now)
                data['recovery_last_quote']=q
                data['recovery_last_pnl_sol']=pnl
                data['recovery_last_attempt_at']=now
                if not should_exit:
                    data['recovery_next_at']=now+RECOVERY_RETRY_SECONDS
                    best=data.get('recovery_best_pnl_sol')
                    if best is None or pnl>best:
                        data['recovery_best_pnl_sol']=pnl; data['recovery_best_quote']=q
                    await save(c,row,'recovery',data,'recovery_waiting_for_breakeven')
                    return
                data['recovery_exit_reason']=why
                balance=await asyncio.to_thread(wallet_balance_sol)
                if balance<RESERVE_SOL: raise ValueError('exit_fee_reserve')
                await submit(c,row,data,q,'exit')
        except QuoteValidationRejected as e:
            # Any live exit quote failure is handled above as inventory recovery.
            # Reaching here therefore means a pre-entry/local validation failure.
            if row:
                current=await c.fetchrow('SELECT * FROM canary_trade_intents WHERE id=$1',row['id'])
                await save(c,current,'rejected',json.loads(current['execution']),'quote_'+e.code)
        except Exception as e:
            # Exception bodies can contain credential-bearing URLs. Persist a safe
            # ValueError label when available; otherwise keep only the exception type.
            safe_reason=(str(e) if isinstance(e,ValueError) and str(e) else type(e).__name__)
            if row:
                current=await c.fetchrow('SELECT * FROM canary_trade_intents WHERE id=$1',row['id'])
                if current['status'] in ('ready','claimed'):
                    await save(c,current,'rejected',json.loads(current['execution']),safe_reason)
                elif current['status'] in ('submitting_entry','submitting_exit') and not json.loads(current['execution']).get(json.loads(current['execution']).get('pending_leg','entry')+'_signature'):
                    await save(c,current,'uncertain',json.loads(current['execution']),'submission_outcome_unknown')
            await halt(c,safe_reason)
        finally:
            await c.execute('SELECT pg_advisory_unlock($1)',LOCK)

async def command(action):
    await init_db(); await schema()
    async with connection() as c:
        if action=='health':
            if not await c.fetchval("SELECT heartbeat > now()-interval '180 seconds' FROM canary_control WHERE id=1"):
                raise ValueError('stale_heartbeat')
            return
        if action=='status':
            control=dict(await c.fetchrow('SELECT * FROM canary_control WHERE id=1'))
            rows=await c.fetch("SELECT id,candidate_id,mint,status,reason,broadcast,updated_at,execution->>'mode' mode,execution->>'exit_at' exit_at FROM canary_trade_intents ORDER BY id DESC LIMIT 12")
            print(json.dumps(dict(control=control,limits=dict(max_trade_gbp=1,wallet_floor_gbp=0,min_consensus=0,min_votes=1,reserve_sol=RESERVE_SOL,max_positions=1),intents=[dict(r) for r in rows]),default=str)); return
        if action=='stop':
            await halt(c,'operator_stop'); print('DISARMED and STOPPED; positions are retained, no automatic liquidation.'); return
        if action=='recover':
            async with c.transaction():
                await c.execute('SELECT pg_advisory_xact_lock($1)',LOCK)
                n=await c.fetchval("SELECT count(*) FROM canary_trade_intents WHERE status IN ('open','recovery','submitting_exit') AND execution->>'mode'='live'")
                if not n: raise ValueError('no_live_inventory_to_recover')
                if wallet_address()!=EXPECTED: raise ValueError('wallet_mismatch')
                await c.execute("UPDATE canary_control SET armed=false,stopped=false,recovery_only=true,problem=null WHERE id=1")
            print('RECOVERY ONLY: exits enabled, new entries disabled'); return
        if action in ('dry-run','arm'):
            async with c.transaction():
                await c.execute('SELECT pg_advisory_xact_lock($1)',LOCK)
                if await c.fetchval("SELECT count(*) FROM canary_trade_intents WHERE status IN ('claimed','open','recovery','submitting_entry','submitting_exit','uncertain')"):
                    raise ValueError('unresolved_position')
                if action=='arm':
                    if not await c.fetchval("SELECT 1 FROM canary_trade_intents WHERE status='closed' AND execution->>'mode'='dry' AND execution ? 'exit_quote' AND execution ? 'eligible_since' AND observed_at >= (execution->>'eligible_since')::timestamptz AND broadcast=false LIMIT 1"):
                        raise ValueError('completed_future_dry_run_required')
                    if wallet_address()!=EXPECTED: raise ValueError('wallet_mismatch')
                    # Fresh preflight quote, funding and FX must all work before arming.
                    rate,source=await asyncio.to_thread(sol_gbp_rate)
                    if source!='kraken_public' or (await asyncio.to_thread(wallet_balance_sol)-RESERVE_SOL)*rate<5: raise ValueError('funding_or_fx')
                await c.execute('UPDATE canary_control SET armed=$1,stopped=false,recovery_only=false,since=now(),problem=null WHERE id=1',action=='arm')
            print('ARMED LIVE' if action=='arm' else 'DRY RUN waiting for a genuine future Reversal intent'); return
    while True:
        await tick(); await asyncio.sleep(5)

if __name__=='__main__':
    try: asyncio.run(command(sys.argv[1] if len(sys.argv)>1 else 'run'))
    except Exception as e: print(json.dumps({'ok':False,'error':type(e).__name__})); sys.exit(1)

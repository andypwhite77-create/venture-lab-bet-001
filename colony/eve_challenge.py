"""Prospective Eve-vs-Ants paper challenge.

Frozen policy, no signer, no broadcast authority, no retroactive scoring.
Every decision is made only from fields present on research_candidates at observation time.
"""
from __future__ import annotations
import json
from colony.paper_economics import sol_gbp_rate

CHALLENGE_VERSION='eve-challenge-v1'
START_AFTER_CANDIDATE_ID=3935
STAKE_GBP=5.0
HOLD_MINUTES=5


def _json(v):
    if isinstance(v,str):
        try:return json.loads(v)
        except Exception:return {}
    try:return dict(v or {})
    except Exception:return {}


def decide(row):
    """Frozen before first scored candidate. Returns (trade, reason, diagnostics)."""
    f=_json(row.get('features')); m=_json(row.get('market'))
    score=float(row.get('score') or 0.0)
    m5=float(f.get('price_change_m5') if f.get('price_change_m5') is not None else m.get('price_change_m5') or 0.0)
    h1=float(f.get('price_change_h1') if f.get('price_change_h1') is not None else m.get('price_change_h1') or 0.0)
    buy=float(f.get('dex_buy_ratio_m5') or 0.0)
    liq=float(f.get('liquidity_usd') if f.get('liquidity_usd') is not None else m.get('liquidity_usd') or 0.0)
    vl=float(f.get('volume_liquidity_m5') or 0.0)
    vol=float(f.get('volume_m5') if f.get('volume_m5') is not None else m.get('volume_m5') or 0.0)
    d={'score':score,'price_change_m5':m5,'price_change_h1':h1,'buy_ratio_m5':buy,
       'liquidity_usd':liq,'volume_liquidity_m5':vl,'volume_m5':vol}
    gates=[
      ('score', score>=0.80),
      ('reversal_drop', -30.0<=m5<=-7.0),
      ('buy_pressure', buy>=0.78),
      ('liquidity', liq>=100_000),
      ('activity', vol>=10_000 and 0.015<=vl<=0.35),
      ('not_freefall_h1', h1>=-30.0),
    ]
    failed=[name for name,ok in gates if not ok]
    if failed:return False,'reject:'+','.join(failed),d
    return True,'trade:high-conviction-short-reversal',d


async def ensure_schema(conn):
    await conn.execute("""CREATE TABLE IF NOT EXISTS eve_challenge_state(
      id int PRIMARY KEY CHECK(id=1), challenge_version text NOT NULL,
      start_after_candidate_id bigint NOT NULL, last_candidate_id bigint NOT NULL,
      started_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE IF NOT EXISTS eve_challenge_decisions(
      id bigserial PRIMARY KEY, challenge_version text NOT NULL,
      candidate_id bigint NOT NULL UNIQUE, observed_at timestamptz NOT NULL,
      mint text NOT NULL, decision text NOT NULL CHECK(decision IN ('trade','abstain')),
      reason text NOT NULL, stake_gbp double precision NOT NULL,
      hold_minutes int NOT NULL, diagnostics jsonb NOT NULL DEFAULT '{}',
      created_at timestamptz NOT NULL DEFAULT now());""")
    row=await conn.fetchrow('SELECT * FROM eve_challenge_state WHERE id=1')
    if not row:
        await conn.execute("""INSERT INTO eve_challenge_state(id,challenge_version,start_after_candidate_id,last_candidate_id)
          VALUES(1,$1,$2,$2)""",CHALLENGE_VERSION,START_AFTER_CANDIDATE_ID)


async def run_once(conn,limit=1000):
    await ensure_schema(conn)
    s=await conn.fetchrow('SELECT * FROM eve_challenge_state WHERE id=1 FOR UPDATE')
    if s['challenge_version']!=CHALLENGE_VERSION or int(s['start_after_candidate_id'])!=START_AFTER_CANDIDATE_ID:
        raise RuntimeError('eve_challenge_frozen_state_mismatch')
    rows=await conn.fetch("""SELECT id,created_at,mint,score,features,market FROM research_candidates
      WHERE id>$1 ORDER BY id LIMIT $2""",int(s['last_candidate_id']),int(limit))
    trades=abstain=0
    for r in rows:
        rr=dict(r); trade,reason,diag=decide(rr)
        res=await conn.execute("""INSERT INTO eve_challenge_decisions(
          challenge_version,candidate_id,observed_at,mint,decision,reason,stake_gbp,hold_minutes,diagnostics)
          VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb) ON CONFLICT(candidate_id) DO NOTHING""",
          CHALLENGE_VERSION,rr['id'],rr['created_at'],rr['mint'],'trade' if trade else 'abstain',reason,
          STAKE_GBP,HOLD_MINUTES,json.dumps(diag))
        if res.endswith('1'):
            trades+=int(trade);abstain+=int(not trade)
    if rows:
        await conn.execute('UPDATE eve_challenge_state SET last_candidate_id=$1,updated_at=now() WHERE id=1',rows[-1]['id'])
    return {'version':CHALLENGE_VERSION,'candidates':len(rows),'trades':trades,'abstain':abstain,
            'last_candidate_id':rows[-1]['id'] if rows else int(s['last_candidate_id'])}


async def stats(conn):
    await ensure_schema(conn)
    rows=await conn.fetch("""SELECT d.*,o.raw_return_pct,o.assumed_cost_bps,o.net_return_pct,o.measured_at
      FROM eve_challenge_decisions d LEFT JOIN research_outcomes o
      ON o.candidate_id=d.candidate_id AND o.horizon_minutes=d.hold_minutes
      ORDER BY d.candidate_id""")
    trades=[r for r in rows if r['decision']=='trade']
    closed=[r for r in trades if r['net_return_pct'] is not None]
    vals=[float(r['net_return_pct']) for r in closed]
    net_gbp=sum(float(r['stake_gbp'])*float(r['net_return_pct'])/100.0 for r in closed)
    return {'version':CHALLENGE_VERSION,'start_after_candidate_id':START_AFTER_CANDIDATE_ID,
      'decisions':len(rows),'trades':len(trades),'abstentions':len(rows)-len(trades),'closed':len(closed),
      'pending':len(trades)-len(closed),'wins':sum(v>0 for v in vals),
      'win_rate':(sum(v>0 for v in vals)/len(vals) if vals else None),
      'mean_net_return_pct':(sum(vals)/len(vals) if vals else None),
      'net_gbp':net_gbp,'paper_balance_gbp':STAKE_GBP+net_gbp}

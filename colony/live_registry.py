"""Live-candidate registry and treasury policy.

Research evidence may nominate candidates, but only canary evidence can make an ant
live-ready.  Treasury accounting is configuration/ledger only; signing and transfers
remain isolated from this module.
"""
from __future__ import annotations
import json

PROMOTION_STAGES = {
    "reference-testing", "canary-ready", "canary-running", "live-ready", "live", "blocked", "retired"
}

FAMILY_MAP = {
    "deep_reversal": "reversal",
    "short_momentum": "momentum",
    "order_flow_tempered": "order_flow",
    "trend_pullback": "pullback",
    "low_churn": "liquidity",
}

async def ensure_schema(conn):
    await conn.execute("""CREATE TABLE IF NOT EXISTS live_ant_registry(
      id BIGSERIAL PRIMARY KEY,
      genome_id TEXT UNIQUE NOT NULL,
      family TEXT NOT NULL,
      species TEXT,
      lineage TEXT NOT NULL,
      source TEXT NOT NULL,
      genome JSONB NOT NULL,
      live_candidate BOOLEAN NOT NULL DEFAULT true,
      promotion_stage TEXT NOT NULL DEFAULT 'reference-testing',
      spartan_passed BOOLEAN NOT NULL DEFAULT false,
      spartan_passed_at TIMESTAMPTZ,
      canary_profile TEXT NOT NULL DEFAULT 'individual-ant-v1',
      canary_passed BOOLEAN NOT NULL DEFAULT false,
      canary_passed_at TIMESTAMPTZ,
      live_authorized BOOLEAN NOT NULL DEFAULT false,
      evidence_version TEXT,
      notes JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CHECK(promotion_stage IN ('reference-testing','canary-ready','canary-running','live-ready','live','blocked','retired'))
    );
    CREATE INDEX IF NOT EXISTS live_ant_registry_family_stage ON live_ant_registry(family,promotion_stage);
    CREATE TABLE IF NOT EXISTS live_ant_canary_runs(
      id BIGSERIAL PRIMARY KEY,
      ant_id BIGINT NOT NULL REFERENCES live_ant_registry(id) ON DELETE CASCADE,
      profile TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      independent_opportunities INT NOT NULL DEFAULT 0,
      closed_trades INT NOT NULL DEFAULT 0,
      realized_net_gbp DOUBLE PRECISION NOT NULL DEFAULT 0,
      worst_drawdown_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
      execution_coverage DOUBLE PRECISION NOT NULL DEFAULT 0,
      execution_faults INT NOT NULL DEFAULT 0,
      started_at TIMESTAMPTZ,
      completed_at TIMESTAMPTZ,
      detail JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS treasury_policy(
      id INT PRIMARY KEY CHECK(id=1),
      enabled BOOLEAN NOT NULL DEFAULT false,
      auto_withdraw_enabled BOOLEAN NOT NULL DEFAULT false,
      personal_wallet_id BIGINT REFERENCES admin_wallets(id) ON DELETE SET NULL,
      withdraw_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
      reinvest_pct DOUBLE PRECISION NOT NULL DEFAULT 100,
      withdraw_trigger_gbp DOUBLE PRECISION NOT NULL DEFAULT 20,
      reinvest_trigger_gbp DOUBLE PRECISION NOT NULL DEFAULT 5,
      min_operating_bankroll_gbp DOUBLE PRECISION NOT NULL DEFAULT 25,
      max_family_exposure_pct DOUBLE PRECISION NOT NULL DEFAULT 40,
      max_ant_stake_gbp DOUBLE PRECISION NOT NULL DEFAULT 25,
      settlement_basis TEXT NOT NULL DEFAULT 'portfolio_high_watermark',
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      CHECK(withdraw_pct>=0 AND withdraw_pct<=100),
      CHECK(reinvest_pct>=0 AND reinvest_pct<=100),
      CHECK(abs((withdraw_pct+reinvest_pct)-100)<0.000001),
      CHECK(withdraw_trigger_gbp>0), CHECK(reinvest_trigger_gbp>0),
      CHECK(min_operating_bankroll_gbp>=0),
      CHECK(max_family_exposure_pct>0 AND max_family_exposure_pct<=100),
      CHECK(max_ant_stake_gbp>0)
    );
    INSERT INTO treasury_policy(id) VALUES(1) ON CONFLICT DO NOTHING;
    CREATE TABLE IF NOT EXISTS treasury_state(
      id INT PRIMARY KEY CHECK(id=1),
      realized_pnl_gbp DOUBLE PRECISION NOT NULL DEFAULT 0,
      allocated_high_watermark_gbp DOUBLE PRECISION NOT NULL DEFAULT 0,
      pending_withdraw_gbp DOUBLE PRECISION NOT NULL DEFAULT 0,
      pending_reinvest_gbp DOUBLE PRECISION NOT NULL DEFAULT 0,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    INSERT INTO treasury_state(id) VALUES(1) ON CONFLICT DO NOTHING;
    CREATE TABLE IF NOT EXISTS treasury_events(
      id BIGSERIAL PRIMARY KEY,
      ant_id BIGINT REFERENCES live_ant_registry(id) ON DELETE SET NULL,
      family TEXT,
      event_type TEXT NOT NULL,
      amount_gbp DOUBLE PRECISION NOT NULL,
      detail JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );""")


def strategy_family(genome, fallback="queen_pattern"):
    species=(genome or {}).get("species")
    return FAMILY_MAP.get(species, species or (genome or {}).get("family") or fallback)


async def sync_spartan_passers(conn):
    await ensure_schema(conn)
    rows=await conn.fetch("""SELECT family,genome_id,genome,archived_at,source_run_id,exam_snapshot_sha256
      FROM spartan_hall_of_fame WHERE qualification_pass=true ORDER BY archived_at""")
    changed=0
    for r in rows:
        g=r['genome']; g=json.loads(g) if isinstance(g,str) else dict(g or {})
        family=strategy_family(g,r['family']); species=g.get('species') or g.get('family')
        res=await conn.execute("""INSERT INTO live_ant_registry(
          genome_id,family,species,lineage,source,genome,promotion_stage,spartan_passed,spartan_passed_at,
          canary_profile,evidence_version,notes)
          VALUES($1,$2,$3,$4,'spartan',$5::jsonb,'canary-ready',true,$6,'individual-ant-v1',$7,$8::jsonb)
          ON CONFLICT(genome_id) DO UPDATE SET family=excluded.family,species=excluded.species,
            lineage=excluded.lineage,spartan_passed=true,spartan_passed_at=COALESCE(live_ant_registry.spartan_passed_at,excluded.spartan_passed_at),
            promotion_stage=CASE WHEN live_ant_registry.canary_passed THEN 'live-ready' ELSE 'canary-ready' END,
            evidence_version=excluded.evidence_version,updated_at=now()""",
          r['genome_id'],family,species,r['family'],json.dumps(g),r['archived_at'],r['exam_snapshot_sha256'],
          json.dumps({'source_run_id':r['source_run_id']}))
        changed += int(res.endswith('1'))
    return {'passing':len(rows),'synced':changed}


async def seed_reference_ants(conn, benchmark):
    """Register only the five designed ants; the naive control is not a live candidate."""
    await ensure_schema(conn)
    n=0
    for item in benchmark.get('ants',[]):
        g=item.get('genome') or {}
        species=item.get('species') or g.get('species')
        if species=='control_buy_all':
            continue
        gid=item.get('genome_id')
        if not gid or not g:
            continue
        family=FAMILY_MAP.get(species,species or 'eve_reference')
        await conn.execute("""INSERT INTO live_ant_registry(
          genome_id,family,species,lineage,source,genome,live_candidate,promotion_stage,spartan_passed,
          canary_profile,evidence_version,notes)
          VALUES($1,$2,$3,'eve_reference_v2','eve_reference',$4::jsonb,true,'reference-testing',false,
                 'individual-ant-v1','eve-reference-v2',$5::jsonb)
          ON CONFLICT(genome_id) DO UPDATE SET family=excluded.family,species=excluded.species,
            lineage=excluded.lineage,source=excluded.source,genome=excluded.genome,live_candidate=true,
            evidence_version=excluded.evidence_version,notes=excluded.notes,updated_at=now()""",
          gid,family,species,json.dumps(g),json.dumps({'freeze_sha256':benchmark.get('freeze_sha256'),
          'prospective_after':benchmark.get('prospective_after'),'walk_forward':item.get('folds') or item.get('walk_forward')}))
        n+=1
    return {'reference_candidates':n}


async def record_canary_result(conn, ant_id, passed, detail=None):
    """Canary may promote only a Spartan-proven candidate; it never grants live authority."""
    await ensure_schema(conn)
    async with conn.transaction():
        ant=await conn.fetchrow('SELECT * FROM live_ant_registry WHERE id=$1 FOR UPDATE',ant_id)
        if not ant: raise ValueError('ant_not_found')
        if passed and not ant['spartan_passed']:
            raise ValueError('spartan_pass_required_before_live_ready')
        stage='live-ready' if passed else 'blocked'
        await conn.execute("""UPDATE live_ant_registry SET canary_passed=$2,canary_passed_at=CASE WHEN $2 THEN now() ELSE NULL END,
          promotion_stage=$3,live_authorized=false,updated_at=now() WHERE id=$1""",ant_id,bool(passed),stage)
        await conn.execute("""INSERT INTO live_ant_canary_runs(ant_id,profile,status,completed_at,detail)
          VALUES($1,$2,$3,now(),$4::jsonb)""",ant_id,ant['canary_profile'],'passed' if passed else 'failed',json.dumps(detail or {}))
    return {'ant_id':ant_id,'canary_passed':bool(passed),'promotion_stage':stage,'live_authorized':False}


async def set_live_authority(conn, ant_id, enabled):
    """Human authority switch. Evidence gates cannot be bypassed when enabling."""
    await ensure_schema(conn)
    async with conn.transaction():
        ant=await conn.fetchrow('SELECT * FROM live_ant_registry WHERE id=$1 FOR UPDATE',ant_id)
        if not ant: raise ValueError('ant_not_found')
        if enabled:
            if not ant['spartan_passed']: raise ValueError('spartan_pass_required')
            if not ant['canary_passed']: raise ValueError('canary_pass_required')
            if ant['promotion_stage'] not in ('live-ready','live'): raise ValueError('ant_not_live_ready')
            await conn.execute("UPDATE live_ant_registry SET live_authorized=true,promotion_stage='live',updated_at=now() WHERE id=$1",ant_id)
            stage='live'
        else:
            stage='live-ready' if ant['canary_passed'] and ant['spartan_passed'] else ant['promotion_stage']
            await conn.execute('UPDATE live_ant_registry SET live_authorized=false,promotion_stage=$2,updated_at=now() WHERE id=$1',ant_id,stage)
    return {'ant_id':ant_id,'live_authorized':bool(enabled),'promotion_stage':stage}


async def treasury_snapshot(conn):
    await ensure_schema(conn)
    p=dict(await conn.fetchrow('SELECT * FROM treasury_policy WHERE id=1'))
    s=dict(await conn.fetchrow('SELECT * FROM treasury_state WHERE id=1'))
    return {'policy':p,'state':s}


def validate_policy(p):
    w=float(p['withdraw_pct']); r=float(p['reinvest_pct'])
    if abs(w+r-100)>1e-6: raise ValueError('profit_split_must_equal_100')
    if not 0<=w<=100 or not 0<=r<=100: raise ValueError('bad_profit_split')
    for k in ('withdraw_trigger_gbp','reinvest_trigger_gbp','max_ant_stake_gbp'):
        if float(p[k])<=0: raise ValueError('bad_'+k)
    if float(p['min_operating_bankroll_gbp'])<0: raise ValueError('bad_bankroll_floor')
    if not 0<float(p['max_family_exposure_pct'])<=100: raise ValueError('bad_family_cap')
    return p


async def update_treasury_policy(conn, values):
    current=dict(await conn.fetchrow('SELECT * FROM treasury_policy WHERE id=1'))
    merged={**current,**values}; validate_policy(merged)
    return dict(await conn.fetchrow("""UPDATE treasury_policy SET enabled=$1,auto_withdraw_enabled=$2,
      personal_wallet_id=$3,withdraw_pct=$4,reinvest_pct=$5,withdraw_trigger_gbp=$6,reinvest_trigger_gbp=$7,
      min_operating_bankroll_gbp=$8,max_family_exposure_pct=$9,max_ant_stake_gbp=$10,updated_at=now()
      WHERE id=1 RETURNING *""",bool(merged['enabled']),bool(merged['auto_withdraw_enabled']),merged.get('personal_wallet_id'),
      float(merged['withdraw_pct']),float(merged['reinvest_pct']),float(merged['withdraw_trigger_gbp']),
      float(merged['reinvest_trigger_gbp']),float(merged['min_operating_bankroll_gbp']),
      float(merged['max_family_exposure_pct']),float(merged['max_ant_stake_gbp'])))


async def record_realized_pnl(conn, amount_gbp, ant_id=None, family=None, detail=None):
    """High-watermark accounting. Losses must be recovered before more profit is allocated."""
    await ensure_schema(conn)
    amount=float(amount_gbp)
    async with conn.transaction():
        state=dict(await conn.fetchrow('SELECT * FROM treasury_state WHERE id=1 FOR UPDATE'))
        policy=dict(await conn.fetchrow('SELECT * FROM treasury_policy WHERE id=1'))
        realized=float(state['realized_pnl_gbp'])+amount
        old_hw=float(state['allocated_high_watermark_gbp'])
        new_profit=max(0.0,realized-old_hw)
        wd=float(state['pending_withdraw_gbp']); ri=float(state['pending_reinvest_gbp'])
        new_hw=old_hw
        if new_profit>0:
            wd += new_profit*float(policy['withdraw_pct'])/100.0
            ri += new_profit*float(policy['reinvest_pct'])/100.0
            new_hw=realized
        await conn.execute("""UPDATE treasury_state SET realized_pnl_gbp=$1,allocated_high_watermark_gbp=$2,
          pending_withdraw_gbp=$3,pending_reinvest_gbp=$4,updated_at=now() WHERE id=1""",realized,new_hw,wd,ri)
        await conn.execute("INSERT INTO treasury_events(ant_id,family,event_type,amount_gbp,detail) VALUES($1,$2,'realized_pnl',$3,$4::jsonb)",
                           ant_id,family,amount,json.dumps(detail or {}))
    return {'realized_pnl_gbp':realized,'new_profit_allocated_gbp':new_profit,'pending_withdraw_gbp':wd,
            'pending_reinvest_gbp':ri,'withdraw_ready':bool(policy['enabled'] and policy['auto_withdraw_enabled'] and wd>=float(policy['withdraw_trigger_gbp'])),
            'reinvest_ready':bool(policy['enabled'] and ri>=float(policy['reinvest_trigger_gbp']))}

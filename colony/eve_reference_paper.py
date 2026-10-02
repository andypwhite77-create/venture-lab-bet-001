"""Continuous forward paper trading for frozen Eve reference ants.

No signer and no live authority. Reference genomes are never mutated here. Their
forward outcomes are exposed to Queen experience as quarantined training evidence;
the same mints are excluded from Queen validation/holdout by queen_experience.
"""
from __future__ import annotations
import json
from colony.forward import eligible
from colony.paper_economics import TARGET_STAKE_GBP, adjusted_return_pct, measured_roundtrip_network_fee_sol, sol_gbp_rate

async def ensure_schema(conn):
    await conn.execute("""CREATE TABLE IF NOT EXISTS eve_reference_paper_progress(
      id INT PRIMARY KEY CHECK(id=1), last_candidate_id BIGINT NOT NULL DEFAULT 0,
      initialized_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
    INSERT INTO eve_reference_paper_progress(id) VALUES(1) ON CONFLICT DO NOTHING;
    CREATE TABLE IF NOT EXISTS eve_reference_paper_entries(
      id BIGSERIAL PRIMARY KEY,
      ant_id BIGINT NOT NULL REFERENCES live_ant_registry(id) ON DELETE CASCADE,
      genome_id TEXT NOT NULL,
      family TEXT NOT NULL,
      species TEXT,
      mint TEXT NOT NULL,
      candidate_id BIGINT NOT NULL,
      observed_at TIMESTAMPTZ NOT NULL,
      hold_minutes INT NOT NULL,
      stake_gbp DOUBLE PRECISION NOT NULL DEFAULT 25,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE(genome_id,candidate_id));
    CREATE INDEX IF NOT EXISTS eve_reference_paper_genome_time ON eve_reference_paper_entries(genome_id,observed_at);
    CREATE INDEX IF NOT EXISTS eve_reference_paper_candidate ON eve_reference_paper_entries(candidate_id);""")


def _json(v):
    if isinstance(v,str):
        try:return json.loads(v)
        except Exception:return {}
    return dict(v or {})

async def _ants(conn):
    rows=await conn.fetch("""SELECT id,genome_id,family,species,genome,notes
      FROM live_ant_registry WHERE source='eve_reference' AND live_candidate=true
      ORDER BY id""")
    out=[]
    for r in rows:
        g=_json(r['genome']); notes=_json(r['notes'])
        if (g.get('species') or r['species'])=='control_buy_all': continue
        out.append({'id':r['id'],'genome_id':r['genome_id'],'family':r['family'],'species':r['species'],
                    'genome':g,'prospective_after':float(notes.get('prospective_after') or 0)})
    return out

async def run_once(conn, limit=1000):
    await ensure_schema(conn)
    ants=await _ants(conn)
    if not ants:return {'ants':0,'candidates':0,'entries':0,'reason':'no_reference_ants'}
    cutoff=max(a['prospective_after'] for a in ants)
    progress=await conn.fetchrow('SELECT * FROM eve_reference_paper_progress WHERE id=1 FOR UPDATE')
    last=int(progress['last_candidate_id'] or 0)
    if not progress['initialized_at']:
        last=int(await conn.fetchval("SELECT coalesce(max(id),0) FROM research_candidates WHERE created_at < to_timestamp($1)",cutoff) or 0)
        await conn.execute('UPDATE eve_reference_paper_progress SET last_candidate_id=$1,initialized_at=now(),updated_at=now() WHERE id=1',last)
    rows=await conn.fetch("""SELECT id,created_at,mint,features,market FROM research_candidates
      WHERE id>$1 AND created_at>=to_timestamp($2) ORDER BY id LIMIT $3""",last,cutoff,int(limit))
    inserted=0; hits={a['genome_id']:0 for a in ants}
    latest={}
    if rows:
        prev=await conn.fetch("""SELECT DISTINCT ON(genome_id,mint) genome_id,mint,observed_at
          FROM eve_reference_paper_entries ORDER BY genome_id,mint,observed_at DESC""")
        latest={(r['genome_id'],r['mint']):r['observed_at'] for r in prev}
    for row in rows:
        rr=dict(row)
        for a in ants:
            hold=int(a['genome'].get('parameters',{}).get('hold_minutes',15))
            previous=latest.get((a['genome_id'],rr['mint']))
            # A paper ant cannot open overlapping positions in the same mint. Even when
            # the genome has no explicit cooldown, its own hold horizon is the minimum re-entry interval.
            if previous is not None and (rr['created_at']-previous).total_seconds() < hold*60:
                continue
            if not eligible(a['genome'],rr,None):continue
            res=await conn.execute("""INSERT INTO eve_reference_paper_entries(
              ant_id,genome_id,family,species,mint,candidate_id,observed_at,hold_minutes,stake_gbp)
              VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT DO NOTHING""",
              a['id'],a['genome_id'],a['family'],a['species'],rr['mint'],rr['id'],rr['created_at'],hold,TARGET_STAKE_GBP)
            if res.endswith('1'):
                inserted+=1;hits[a['genome_id']]+=1;latest[(a['genome_id'],rr['mint'])]=rr['created_at']
    if rows:
        await conn.execute('UPDATE eve_reference_paper_progress SET last_candidate_id=$1,updated_at=now() WHERE id=1',rows[-1]['id'])
    return {'ants':len(ants),'candidates':len(rows),'entries':inserted,'hits':hits,'last_candidate_id':rows[-1]['id'] if rows else last}

async def stats(conn):
    await ensure_schema(conn)
    ants=await _ants(conn)
    fee_sol=await measured_roundtrip_network_fee_sol(conn); rate,_=sol_gbp_rate(); fixed_gbp=fee_sol*rate
    rows=await conn.fetch("""SELECT e.genome_id,e.family,e.species,e.mint,e.candidate_id,e.observed_at,e.hold_minutes,e.stake_gbp,
      (SELECT o.net_return_pct FROM research_outcomes o WHERE o.candidate_id=e.candidate_id
       AND o.horizon_minutes=e.hold_minutes AND o.measured_at>=e.observed_at ORDER BY o.measured_at DESC LIMIT 1) raw_return_pct
      FROM eve_reference_paper_entries e ORDER BY e.observed_at""")
    by={a['genome_id']:{'genome_id':a['genome_id'],'family':a['family'],'species':a['species'],'entries':0,'closed':0,'pending':0,
                            'wins':0,'net_gbp':0.0,'returns':[],'unique_mints':set()} for a in ants}
    for r in rows:
        z=by.setdefault(r['genome_id'],{'genome_id':r['genome_id'],'family':r['family'],'species':r['species'],'entries':0,'closed':0,'pending':0,'wins':0,'net_gbp':0.0,'returns':[],'unique_mints':set()})
        z['entries']+=1; z['unique_mints'].add(r['mint'])
        if r['raw_return_pct'] is None:z['pending']+=1;continue
        stake=float(r['stake_gbp'] or TARGET_STAKE_GBP); adj=adjusted_return_pct(float(r['raw_return_pct']),stake,fixed_gbp)
        z['closed']+=1;z['wins']+=int(adj>0);z['returns'].append(adj);z['net_gbp']+=stake*adj/100.0
    out=[]
    for a in ants:
        z=by[a['genome_id']]; vals=z.pop('returns'); mints=z.pop('unique_mints')
        z.update(unique_mints=len(mints),win_rate=(z['wins']/z['closed'] if z['closed'] else None),
                 mean_net_return_pct=(sum(vals)/len(vals) if vals else None),net_gbp=round(z['net_gbp'],6),
                 paper_balance_gbp=round(TARGET_STAKE_GBP+z['net_gbp'],6),fixed_roundtrip_cost_gbp=round(fixed_gbp,6))
        out.append(z)
    return out

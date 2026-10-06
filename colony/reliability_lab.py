"""Bounded research-only tail-repair descendants for Champion challengers.

Uses only breeding-visible corpus/failure patterns. Descendants get no inherited
performance and must earn fresh prospective evidence after enrolment.
"""
from __future__ import annotations
import copy,json
from colony.genome import genome_id

PARENTS=(
 'g_3c9714b448cc8104',
 'g_4b3c30554fca627e',
 'g_abec3d527f9ee1cb',
 'g_c5d4c6446408a195',
)

def _variant(parent_gid,g,kind):
    x=copy.deepcopy(g)
    x['parents']=[parent_gid]
    x['family']=x.get('family') or 'reliability_lab'
    x['reliability_lab']={'parent':parent_gid,'kind':kind,'version':1}
    p=x.setdefault('parameters',{})
    pred=x.setdefault('predicates',{})
    if kind=='steady_3':
        p['stop_loss_pct']=-8
        p['take_profit_pct']=3
    elif kind=='steady_5_regime':
        p['stop_loss_pct']=-12
        p['take_profit_pct']=5
        species=x.get('species')
        if species=='pullback_hammer':
            pred.setdefault('price_change_h1',{})['max']=250
        elif species in ('deep_drawdown_bid','quiet_accumulation'):
            pred.setdefault('price_change_m5',{})['max']=0
        elif x.get('family')=='reversal':
            pred.setdefault('price_change_h1',{})['min']=-20
    return x

async def enroll(c):
    cutoff=int(await c.fetchval('SELECT coalesce(max(id),0) FROM research_candidates') or 0)
    added=[]
    for parent_gid in PARENTS:
        r=await c.fetchrow("SELECT genome FROM champion_league WHERE genome_id=$1",parent_gid)
        if not r: continue
        g=r['genome'] if isinstance(r['genome'],dict) else json.loads(r['genome'])
        for kind in ('steady_3','steady_5_regime'):
            child=_variant(parent_gid,g,kind)
            gid=genome_id(child)
            res=await c.execute("""INSERT INTO champion_league(
                genome_id,family,genome,source,pool,prospective_after_candidate,notes)
              VALUES($1,$2,$3::jsonb,'reliability_lab','qualification',$4,$5::jsonb)
              ON CONFLICT(genome_id) DO NOTHING""",
              gid,child.get('family') or 'reliability_lab',json.dumps(child),cutoff,
              json.dumps({'research_only':True,'parent':parent_gid,'repair':kind,'fresh_prospective_required':True}))
            if res.endswith('1'): added.append({'genome_id':gid,'parent':parent_gid,'kind':kind})
    return {'cutoff':cutoff,'added':added}

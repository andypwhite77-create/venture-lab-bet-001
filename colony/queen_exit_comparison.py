"""Paired, read-only exit-policy experiment on observed candidate price paths.
No fills, promotion, parameter mutation, breeding or trade permissions.
"""
import asyncio, json, statistics, hashlib
from db import init_db, connection
from colony.hive_exit_path_audit import simulate

POLICIES={'stop_10':(-10,None),'stop_20':(-20,None),'take_10':(None,10),'stop_10_take_15':(-10,15)}
SCHEMA="""CREATE TABLE IF NOT EXISTS queen_exit_research_runs (
 id bigserial primary key, created_at timestamptz default now(),
 report jsonb not null, authority text not null default 'observation_only_no_execution');"""

def compare(rows, minimum=30):
    pairs={p:[] for p in POLICIES}; exclusions={}
    for row in rows:
        base=row['control'];
        if base['status']!='observed_path':
            exclusions[base['status']]=exclusions.get(base['status'],0)+1;continue
        for name in POLICIES:
            variant=row[name]
            if variant['status']=='observed_path':
                pairs[name].append((row['candidate_id'],variant['net_pct']-base['net_pct'],variant['net_pct'],base['net_pct']))
    report={}
    for name,observations in pairs.items():
        by_id={x[0]:x for x in observations};vals=list(by_id.values());deltas=[x[1] for x in vals]
        n=len(vals); edge=statistics.fmean(deltas) if deltas else None
        report[name]={'distinct_paired_opportunities':n,'mean_edge_pct_points':round(edge,4) if edge is not None else None,
            'worst_variant_pct':round(min((v[2] for v in vals)),4) if vals else None,
            'worst_control_pct':round(min((v[3] for v in vals)),4) if vals else None,
            'improved_count':sum(v[1]>0 for v in vals),'worsened_count':sum(v[1]<0 for v in vals),
            'status':'exploratory_not_qualified' if n>=minimum else 'insufficient_independent_paths',
            'decision':'more_forward_validation_required' if n>=minimum else 'collect_complete_price_paths'}
    return {'policies':report,'excluded_control_paths':exclusions,
        'limitations':['Retrospective comparison of sampled marks, not executable order fills.',
        'Policies selected before this run but existing samples may have selection bias.',
        'Matched candidates may not be statistically independent.',
        'Fixed 30 bps round-trip friction omits uncertain slippage and impact.',
        'No promotion, breeding, or live trading authority.']}

async def run(limit=500):
    await init_db()
    async with connection() as c:
        await c.execute(SCHEMA)
        entries=await c.fetch("""SELECT DISTINCT ON (e.candidate_id) e.candidate_id,e.observed_at,e.hold_minutes,r.entry_price
          FROM family_tournament_entries e JOIN research_candidates r ON r.id=e.candidate_id
          WHERE e.run_id='hive-loss-tail-1' ORDER BY e.candidate_id,e.observed_at LIMIT $1""",limit)
        ids=[x['candidate_id'] for x in entries]
        samples=await c.fetch("""SELECT candidate_id,observed_at,price FROM research_price_path
            WHERE candidate_id=ANY($1::bigint[]) ORDER BY candidate_id,observed_at""",ids) if ids else []
        paths={}
        for v in samples:paths.setdefault(v['candidate_id'],[]).append((v['observed_at'],v['price']))
        evaluated=[]
        for e in entries:
            a=e['observed_at'];p=float(e['entry_price'] or 0);path=paths.get(e['candidate_id'],[]);hold=e['hold_minutes']
            result={'candidate_id':e['candidate_id'],'control':simulate(a,p,path,hold)}
            for name,(stop,take) in POLICIES.items():
                result[name]=simulate(a,p,path,hold,stop_pct=stop,take_pct=take)
            evaluated.append(result)
        evidence_fingerprint=hashlib.sha256(json.dumps([(r['candidate_id'],r['control'].get('exit_at'),r['control'].get('net_pct'),[(name,r[name].get('net_pct'),r[name].get('exit_at')) for name in POLICIES]) for r in evaluated],default=str).encode()).hexdigest()
        report={'experiment':'fixed_exit_policy_pairs_v1','evidence_fingerprint':evidence_fingerprint,'input_candidates':len(entries),
                'authority':'observation_only_no_breeding_no_spartan_no_live',**compare(evaluated)}
        previous=await c.fetchval("SELECT report->>'evidence_fingerprint' FROM queen_exit_research_runs ORDER BY id DESC LIMIT 1")
        if previous==evidence_fingerprint:
            return {'status':'unchanged_no_new_run','evidence_fingerprint':evidence_fingerprint,'input_candidates':len(entries)}
        rid=await c.fetchval('INSERT INTO queen_exit_research_runs(report) VALUES($1::jsonb) RETURNING id',json.dumps(report))
        return {'id':rid,**report}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

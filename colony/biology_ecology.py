"""Shadow-only eusocial lifecycle telemetry and reproduction policy.
Workers test reality; bloodlines earn reproductive capacity; Queen proposes brood.
No live capital, population mutation, signing or broadcast authority lives here.
"""
from collections import defaultdict
import json
from db import connection
from colony.selection_state import snapshot as selection_snapshot

MIN_WORKER_EVIDENCE=20
MAX_WORKERS_PER_BLOODLINE=50
MAX_NURSERY_PER_BLOODLINE=40
GLOBAL_SOFT_CARRYING_CAPACITY=400


def _stage(n, mean_return):
    if n < 5: return 'egg'
    if n < MIN_WORKER_EVIDENCE: return 'larva'
    if mean_return is None: return 'larva'
    if mean_return > 0: return 'proven_worker'
    return 'worker'

async def snapshot():
    sel=await selection_snapshot()
    ants=sel.get('ants',[])
    by_family=defaultdict(list)
    for a in ants: by_family[a.get('family') or 'unknown'].append(a)
    async with connection() as c:
        scouts=await c.fetch('''SELECT s.id,s.parent_genome_id,s.genome_id,s.genome,s.state,
          count(DISTINCT e.mint) evidence_n,avg(o.net_return_pct) mean_return_pct
          FROM colony_queen_scouts s LEFT JOIN colony_queen_scout_entries e ON e.scout_id=s.id
          LEFT JOIN LATERAL (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=e.candidate_id
            AND measured_at>=e.observed_at ORDER BY abs(horizon_minutes-e.hold_minutes) LIMIT 1) o ON true
          GROUP BY s.id ORDER BY s.id''') if await c.fetchval("SELECT to_regclass('public.colony_queen_scouts') IS NOT NULL") else []
    nursery=defaultdict(list)
    for s in scouts:
        g=s['genome'] if isinstance(s['genome'],dict) else json.loads(s['genome']) if s['genome'] else {}
        fam=g.get('family') or 'unknown'
        n=int(s['evidence_n'] or 0); mean=float(s['mean_return_pct']) if s['mean_return_pct'] is not None else None
        nursery[fam].append({'scout_id':s['id'],'genome_id':s['genome_id'],'parent_genome_id':s['parent_genome_id'],
                             'evidence_n':n,'mean_return_pct':mean,'stage':_stage(n,mean),'state':s['state']})

    families=[]
    all_names=sorted(set(by_family)|set(nursery))
    for fam in all_names:
        workers=by_family.get(fam,[])
        ready=[a for a in workers if int(a.get('n') or 0)>=MIN_WORKER_EVIDENCE]
        positive=[a for a in ready if float(a.get('avg_return_pct') or 0)>0]
        brood=nursery.get(fam,[])
        nursery_count=sum(x.get('state')=='nursery' for x in brood)
        paper_count=sum(x.get('state')=='paper' for x in brood)
        live_ready_count=sum(x.get('state')=='live_ready' for x in brood)
        # Reproductive capacity belongs to the bloodline, not a lucky worker.
        evidence_strength=sum(int(a.get('n') or 0) for a in ready)
        reproductive_credit=min(MAX_NURSERY_PER_BLOODLINE,
                                len(positive)//5 + (1 if evidence_strength>=200 and positive else 0))
        justified_workers=min(MAX_WORKERS_PER_BLOODLINE,
                              max(len(ready), min(MAX_WORKERS_PER_BLOODLINE, len(positive)*2)))
        families.append({'family':fam,'workers':len(workers),'evidence_ready_workers':len(ready),
                         'positive_ready_workers':len(positive),'nursery':nursery_count,'paper':paper_count,'live_ready':live_ready_count,
                         'reproductive_credit':reproductive_credit,
                         'justified_worker_capacity':justified_workers,
                         'worker_soft_cap':MAX_WORKERS_PER_BLOODLINE,
                         'brood':brood})

    total_workers=sum(x['workers'] for x in families)
    total_nursery=sum(x['nursery'] for x in families)
    total_paper=sum(x.get('paper',0) for x in families)
    total_live_ready=sum(x.get('live_ready',0) for x in families)
    justified=sum(x['justified_worker_capacity'] for x in families)
    return {'mode':'shadow_only','organism_model':'eusocial_v1','population_fixed':False,
            'worker_rule':'workers gather evidence; bloodlines earn reproduction; Queen proposes brood',
            'min_worker_evidence':MIN_WORKER_EVIDENCE,'max_workers_per_bloodline':MAX_WORKERS_PER_BLOODLINE,
            'max_nursery_per_bloodline':MAX_NURSERY_PER_BLOODLINE,
            'global_soft_carrying_capacity':GLOBAL_SOFT_CARRYING_CAPACITY,
            'current_workers':total_workers,'current_nursery':total_nursery,'current_paper':total_paper,
            'current_live_ready':total_live_ready,'live_execution_authority':False,
            'lifecycle':'birth -> nursery QC -> paper validation -> live-ready; live capital requires separate authorization',
            'evidence_justified_capacity':min(GLOBAL_SOFT_CARRYING_CAPACITY,justified),
            'bloodlines':families}

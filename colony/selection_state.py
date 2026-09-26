"""Read-only Gen-3 selection telemetry. It cannot reproduce or mutate genomes."""
from collections import defaultdict
from db import connection
from colony.selection import ant_metrics
from colony.resource_ecology import allocation
RUN='fwd-g3-20260926T084022Z'; QUALIFY_N=20; REPRO_SHARE=.49
CONSTITUTION='gen4-adversarial-v1'; EFFECTIVE_EVIDENCE_MODEL='pending-v1'; ABSOLUTE_VIABILITY_REQUIRED=True
async def snapshot():
 async with connection() as c:
  genomes=await c.fetch("SELECT genome_id,family,status FROM colony_genomes WHERE generation=3")
  rows=await c.fetch("""SELECT e.genome_id,e.mint,o.net_return_pct FROM colony_forward_entries e
   JOIN LATERAL (SELECT net_return_pct FROM research_outcomes WHERE candidate_id=e.candidate_id AND measured_at>=e.observed_at
    ORDER BY abs(horizon_minutes-e.hold_minutes) LIMIT 1) o ON true WHERE e.run_id=$1""",RUN)
 by=defaultdict(list)
 for r in rows: by[r['genome_id']].append((r['mint'],float(r['net_return_pct'])))
 ants=[]
 for g in genomes:
  m=ant_metrics(by[g['genome_id']]); ants.append({'genome_id':g['genome_id'],'family':g['family'],'status':g['status'],**m})
 # Rank only qualified ants inside family/niche. No family can win by having more opportunities.
 for fam in {a['family'] for a in ants}:
  q=sorted([a for a in ants if a['family']==fam and a['n']>=QUALIFY_N],key=lambda a:a['fitness'],reverse=True)
  cutoff=max(1,int(len(q)*REPRO_SHARE)) if q else 0
  for i,a in enumerate(q):
   a['family_rank']=i+1; a['asset_diversity_gate']=True
   # Constitutional lock: distinct assets are not yet effective-independent evidence.
   a['effective_evidence_qualified']=False; a['absolute_viability_qualified']=False
   a['qualified']=False; a['breeding_eligible']=False
 for a in ants:
  a.setdefault('asset_diversity_gate',False);a.setdefault('effective_evidence_qualified',False);a.setdefault('absolute_viability_qualified',False);a.setdefault('qualified',False);a.setdefault('breeding_eligible',False);a.setdefault('family_rank',None)
  # Display-only capital privilege. Live authority remains zero.
  famq=[x for x in ants if x['family']==a['family'] and x.get('qualified')]
  rank=(a['family_rank']-1)/max(1,len(famq)-1) if a['family_rank'] else 1.0
  a['ecology']=allocation(rank,a['n'],a.get('catastrophe_rate',0))
 return {'mode':'shadow_read_only','constitution':CONSTITUTION,'run_id':RUN,'qualify_n':QUALIFY_N,'reproductive_share':REPRO_SHARE,'effective_evidence_model':EFFECTIVE_EVIDENCE_MODEL,'absolute_viability_required':ABSOLUTE_VIABILITY_REQUIRED,
  'qualified':sum(a['qualified'] for a in ants),'breeding_eligible':sum(a['breeding_eligible'] for a in ants),'ants':ants}

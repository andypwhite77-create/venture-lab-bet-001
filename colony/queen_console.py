"""Read-only human conversation context for the Queen/Core."""
from db import connection
from colony.niche_pipeline import candidates as niche_candidates
from colony.independence import opportunity_report
from colony.selection_state import snapshot as selection_snapshot
from colony.queen_scouts import active_count as queen_scout_active_count
from colony.biology_ecology import snapshot as biology_snapshot
from colony.drives import snapshot as drives_snapshot

async def context(run_id):
    async with connection() as conn:
        run=await conn.fetchrow("SELECT generation,status,population FROM colony_forward_runs WHERE run_id=$1",run_id)
        latest=await conn.fetchrow("SELECT max(candidate_id) cutoff,count(*) entries FROM colony_forward_entries WHERE run_id=$1",run_id)
        plans=await conn.fetchval("SELECT count(*) FROM colony_shadow_plans WHERE run_id=$1",run_id)
    sel=await selection_snapshot()
    scout_count=await queen_scout_active_count()
    biology=await biology_snapshot()
    drives=await drives_snapshot()
    reproductive_families={b['family'] for b in biology.get('bloodlines',[]) if int(b.get('reproductive_credit') or 0)>0}
    parent_pool=[a for a in sel.get('ants',[]) if a.get('family') in reproductive_families and int(a.get('n') or 0)>=biology.get('min_worker_evidence',20)]
    parents=[]
    for fam in sorted(reproductive_families):
        fam_pool=sorted([a for a in parent_pool if a.get('family')==fam],key=lambda a:a.get('fitness',-999),reverse=True)[:6]
        parents.extend(fam_pool)
    return {'identity':'Queen/Core','authority':'advisory_only','run_id':run_id,
      'generation':run['generation'] if run else None,'frozen':(run['status']=='frozen') if run else None,
      'evidence_cutoff':latest['cutoff'] if latest else None,'entries':latest['entries'] if latest else 0,
      'shadow_plans':plans,'independent_opportunities':await opportunity_report(run_id),
      'niche_candidates':await niche_candidates(run_id),
      'capital_doctrine':{'live_capital':'earned_scarce_revocable','starter_risk_unit_gbp':1.0,'seed_slots':25,'growth_share':0.5,'locked_profit_share':0.5,'family_cap_fraction':0.4,'production_state':'shadow_only'},
      'reproduction_doctrine':{'principle':'workers_test_bloodlines_reproduce_queen_generates_brood','offspring_cost':'scarce_reproductive_resource','descendant_quality_counts':True,'mortality':'operational_extinction_not_data_deletion','nursery_stages':['egg','larva','worker','proven_worker'],'population_fixed':False,'per_bloodline_soft_cap':50,'bloodline_count_fixed':False,'current_stage':'shadow_experiments_only'},
      'bloodline_ecology':biology,
      'colony_drives':drives,
      'queen_experiment_mandate':{'desired_scouts_per_brood':2,'current_active_shadow_scouts':scout_count,'one_bloodline_per_brood':True,'instruction':'Prefer one minimal falsifiable queen_shadow_scouts brood of one or two grounded parents from the SAME bloodline when it can gather useful prospective evidence. Shadow brood never changes mature population or capital.'},
      'candidate_parents':[{'genome_id':a.get('genome_id'),'family':a.get('family'),'evidence_n':a.get('n'),'fitness':a.get('fitness')} for a in parents]}

async def answerable_topics():
    return ['colony status','why an experiment was proposed','current hypotheses','evidence gaps',
            'what the colony has learned','what data it wants next','why Sceptic vetoed something']

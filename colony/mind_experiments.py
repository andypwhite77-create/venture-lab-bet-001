"""Deterministic bridge from reviewed Mind proposals to shadow-only experiments."""
import json
from db import connection
from colony.queen_scouts import create as create_queen_scouts
SUPPORTED={'ablate_selection_feature','compare_selection_rule','raise_evidence_requirement','stratify_by_regime','stratify_by_niche','request_more_data','queen_shadow_scouts'}

async def ensure_schema():
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_mind_experiments(
          id BIGSERIAL PRIMARY KEY,run_id TEXT NOT NULL,created_at TIMESTAMPTZ DEFAULT now(),
          evidence_cutoff BIGINT NOT NULL,experiment_type TEXT NOT NULL,proposal JSONB NOT NULL,
          sceptic JSONB NOT NULL,status TEXT NOT NULL DEFAULT 'shadow_pending')''')

async def instantiate(run_id,cutoff,core,sceptic):
    await ensure_schema(); p=core.get('payload') or {}; et=p.get('experiment_type')
    if core.get('action')!='request_experiment': return {'created':False,'why':'not_experiment'}
    if et not in SUPPORTED: return {'created':False,'why':'unsupported'}
    # Eusocial rule: cheap shadow brood is allowed to be born before selection.
    # Sceptic reviews the brood but does not suppress variation at birth; it can block
    # maturation/promotion later. Non-brood experiments still require accept_for_test.
    if et!='queen_shadow_scouts' and sceptic.get('action')!='accept_for_test':
        return {'created':False,'why':'not_accepted'}
    if et=='queen_shadow_scouts':
        parents=list(dict.fromkeys(p.get('parent_genome_ids') or []))[:2]
        if not parents: return {'created':False,'why':'no_grounded_parents'}
        async with connection() as c:
            rows=await c.fetch("SELECT genome_id,family FROM colony_genomes WHERE genome_id=ANY($1::text[])",parents)
            found={r['genome_id']:r['family'] for r in rows}
            if any(x not in found for x in parents): return {'created':False,'why':'parent_not_grounded'}
            if len({found[x] for x in parents})!=1: return {'created':False,'why':'mixed_bloodline'}
            active=await c.fetchval("SELECT count(*) FROM colony_queen_scouts WHERE state='shadow'")
            if int(active or 0)>=2: return {'created':False,'why':'active_scout_cap','cap':2}
    async with connection() as c:
        eid=await c.fetchval('''INSERT INTO colony_mind_experiments(run_id,evidence_cutoff,experiment_type,proposal,sceptic)
          VALUES($1,$2,$3,$4::jsonb,$5::jsonb) RETURNING id''',run_id,cutoff,et,json.dumps(core),json.dumps(sceptic))
    scouts=None
    if et=='queen_shadow_scouts':
        parents=(p.get('parent_genome_ids') or [])[:2]
        scouts=await create_queen_scouts(eid,run_id,cutoff,parents,max_scouts=2)
    return {'created':True,'experiment_id':eid,'mode':'shadow_only','experiment_type':et,'scouts':scouts}

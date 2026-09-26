"""Deterministic bridge from reviewed Mind proposals to shadow-only experiments."""
import json
from db import connection
SUPPORTED={'ablate_selection_feature','compare_selection_rule','raise_evidence_requirement','stratify_by_regime','stratify_by_niche','request_more_data'}

async def ensure_schema():
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_mind_experiments(
          id BIGSERIAL PRIMARY KEY,run_id TEXT NOT NULL,created_at TIMESTAMPTZ DEFAULT now(),
          evidence_cutoff BIGINT NOT NULL,experiment_type TEXT NOT NULL,proposal JSONB NOT NULL,
          sceptic JSONB NOT NULL,status TEXT NOT NULL DEFAULT 'shadow_pending')''')

async def instantiate(run_id,cutoff,core,sceptic):
    await ensure_schema(); p=core.get('payload') or {}; et=p.get('experiment_type')
    if core.get('action')!='request_experiment': return {'created':False,'why':'not_experiment'}
    if sceptic.get('action')!='accept_for_test': return {'created':False,'why':'not_accepted'}
    if et not in SUPPORTED: return {'created':False,'why':'unsupported'}
    async with connection() as c:
        eid=await c.fetchval('''INSERT INTO colony_mind_experiments(run_id,evidence_cutoff,experiment_type,proposal,sceptic)
          VALUES($1,$2,$3,$4::jsonb,$5::jsonb) RETURNING id''',run_id,cutoff,et,json.dumps(core),json.dumps(sceptic))
    return {'created':True,'experiment_id':eid,'mode':'shadow_only','experiment_type':et}

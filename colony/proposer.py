"""Observer-only experiment proposer. Proposals never mutate the frozen colony."""
import json
from db import connection
from colony.observer import observe
from colony.evidence import assess

async def propose():
    result=await observe()
    if isinstance(result,dict): return result
    board,core,sceptic=result
    gate=assess(core,sceptic)
    if not gate['eligible_for_scout_proposal']:
        return {'created':0,'reason':'evidence_gate','gate':gate}
    proposal={'hypothesis':'test a small scout population against unseen observations',
      'parent_run':board['run_id'],'constraints':{'paper_only':True,'max_scouts':5,
      'cannot_replace_live_ants':True,'same_future_data_as_controls':True},
      'evidence_at_proposal':gate['current']}
    async with connection() as conn:
        exists=await conn.fetchval("SELECT 1 FROM colony_proposals WHERE run_id=$1 AND proposal_type='scout_experiment' AND status='observer_only' LIMIT 1",board['run_id'])
        if exists:return {'created':0,'reason':'existing_proposal','gate':gate}
        pid=await conn.fetchval("INSERT INTO colony_proposals(run_id,proposer,proposal_type,proposal) VALUES($1,'core','scout_experiment',$2::jsonb) RETURNING id",board['run_id'],json.dumps(proposal))
    return {'created':1,'proposal_id':pid,'gate':gate}

"""Wake -> evidence+experience -> Queen -> Sceptic -> journal -> memory -> sleep."""
import json
from db import connection
from colony.queen_console import context
from colony.mind_runtime import infer
from colony.mind_memory import recall,remember,ensure_schema as ensure_memory

async def ensure_schema():
    await ensure_memory()
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_mind_journal(
          id BIGSERIAL PRIMARY KEY, run_id TEXT NOT NULL, observed_at TIMESTAMPTZ DEFAULT now(),
          evidence_cutoff BIGINT, core JSONB, sceptic JSONB, status TEXT NOT NULL)''')

async def wake(run_id):
    await ensure_schema(); evidence=await context(run_id)
    evidence['experience']=await recall(run_id)
    core=await infer('core',evidence,model='qwen3:1.7b')
    sceptic={'ok':False,'validation':'core_failed'}
    if core['ok']:
        review={'evidence':evidence,'core_proposal':core['message']}
        sceptic=await infer('sceptic',review,model='qwen3:1.7b')
    status='reviewed' if core['ok'] and sceptic['ok'] else 'failed_closed'
    async with connection() as c:
        jid=await c.fetchval('''INSERT INTO colony_mind_journal(run_id,evidence_cutoff,core,sceptic,status)
          VALUES($1,$2,$3::jsonb,$4::jsonb,$5) RETURNING id''',run_id,evidence.get('evidence_cutoff'),json.dumps(core),json.dumps(sceptic),status)
    if core['ok']:
        m=core['message']; await remember(run_id,'queen_proposal',m.get('reasoning_summary',''),m.get('payload'),m.get('action'),.4,jid)
    if sceptic['ok']:
        m=sceptic['message']; await remember(run_id,'sceptic_review',m.get('reasoning_summary',''),m.get('payload'),m.get('action'),.5,jid)
    return {'journal_id':jid,'status':status,'core':core,'sceptic':sceptic,'experience_used':len(evidence['experience'])}

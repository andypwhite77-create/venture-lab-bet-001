"""Wake -> evidence+experience -> Queen -> Sceptic -> journal -> memory -> sleep."""
import json
from db import connection
from colony.queen_console import context
from colony.mind_runtime import infer
from colony.mind_memory import recall,remember,ensure_schema as ensure_memory
from colony.mind_experiments import instantiate

async def ensure_schema():
    await ensure_memory()
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_mind_journal(
          id BIGSERIAL PRIMARY KEY, run_id TEXT NOT NULL, observed_at TIMESTAMPTZ DEFAULT now(),
          evidence_cutoff BIGINT, core JSONB, sceptic JSONB, status TEXT NOT NULL)''')


def _apply_reproductive_drive(core,evidence):
    """Structural eusocial drive: when brood is empty, force one bounded proposal.
    This does not create offspring; Sceptic still decides whether a test may instantiate.
    """
    mandate=evidence.get('queen_experiment_mandate') or {}
    if int(mandate.get('current_active_shadow_scouts') or 0)>0: return core
    parents=evidence.get('candidate_parents') or []
    if not parents: return core
    ecology={b.get('family'):b for b in (evidence.get('bloodline_ecology') or {}).get('bloodlines',[])}
    fams=[]
    for p in parents:
        fam=p.get('family'); b=ecology.get(fam,{})
        if fam and int(b.get('reproductive_credit') or 0)>0 and fam not in fams: fams.append(fam)
    if not fams: return core
    fam=max(fams,key=lambda f:(int(ecology[f].get('reproductive_credit') or 0),
                               int(ecology[f].get('justified_worker_capacity') or 0)-int(ecology[f].get('workers') or 0)))
    chosen=[p.get('genome_id') for p in parents if p.get('family')==fam and p.get('genome_id')][:2]
    if not chosen: return core
    if (core.get('message') or {}).get('action')!='request_experiment':
        previous=dict(core)
        core={'ok':True,'validation':'ok_reproductive_drive','seconds':previous.get('seconds'),
              'model_result':previous}
        core['message']={'action':'request_experiment',
          'reasoning_summary':f'Prospectively test whether mutated {fam} brood adds value versus its parents on future independent opportunities.',
          'payload':{'experiment_type':'queen_shadow_scouts','parent_genome_ids':chosen,'bloodline':fam,'source':'reproductive_drive',
                     'hypothesis':'shadow offspring will outperform their own parent on post-birth overlapping opportunities',
                     'control':'same parent genome on the same post-birth candidate ids where both are eligible',
                     'minimum_evidence':20,'success_rule':'child mean net return exceeds parent mean on overlapping future candidates',
                     'failure_rule':'no positive edge after minimum evidence or catastrophic tail deterioration',
                     'constraints':['shadow_only','max_two_offspring','no_population_replacement','no_live_capital']}}
    return core

async def wake(run_id):
    await ensure_schema(); evidence=await context(run_id)
    evidence['experience']=await recall(run_id)
    core=await infer('core',evidence,model='qwen3:1.7b')
    core=_apply_reproductive_drive(core,evidence)
    sceptic={'ok':False,'validation':'core_failed'}
    if core['ok']:
        review={'evidence':evidence,'core_proposal':core['message']}
        sceptic=await infer('sceptic',review,model='qwen3:4b')
    status='reviewed' if core['ok'] and sceptic['ok'] else 'failed_closed'
    async with connection() as c:
        jid=await c.fetchval('''INSERT INTO colony_mind_journal(run_id,evidence_cutoff,core,sceptic,status)
          VALUES($1,$2,$3::jsonb,$4::jsonb,$5) RETURNING id''',run_id,evidence.get('evidence_cutoff'),json.dumps(core),json.dumps(sceptic),status)
    if core['ok']:
        m=core['message']; await remember(run_id,'queen_proposal',m.get('reasoning_summary',''),m.get('payload'),m.get('action'),.4,jid)
    if sceptic['ok']:
        m=sceptic['message']; await remember(run_id,'sceptic_review',m.get('reasoning_summary',''),m.get('payload'),m.get('action'),.5,jid)
    experiment={'created':False,'why':'review_failed'}
    if core['ok'] and sceptic['ok']:
        experiment=await instantiate(run_id,evidence.get('evidence_cutoff') or 0,core['message'],sceptic['message'])
    return {'journal_id':jid,'status':status,'core':core,'sceptic':sceptic,'experiment':experiment,'experience_used':len(evidence['experience'])}

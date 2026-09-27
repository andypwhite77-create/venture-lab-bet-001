"""Asynchronous, fail-closed local Queen/Sceptic inference."""
import json,httpx,time,os,re
from colony.mind_contract import validate
from colony.mind_grounding import validate_grounding,mechanism_packet
OLLAMA=os.getenv('OLLAMA_URL','http://127.0.0.1:11434/api/generate')


def _decode(raw,role,evidence):
    try: return json.loads(raw)
    except Exception:
        m=re.search(r'\"action\"\s*:\s*\"([^\"]+)\"',raw)
        if not m: raise
        action=m.group(1)
        rm=re.search(r'\"reasoning_summary\"\s*:\s*\"([^\"]*)',raw)
        reasoning=(rm.group(1)[:240] if rm else 'Recovered constrained model response')
        payload={}
        if role=='core' and action=='request_experiment' and 'queen_shadow_scouts' in raw:
            allowed={x.get('genome_id') for x in evidence.get('candidate_parents',[]) if isinstance(x,dict)}
            parents=[]
            for gid in re.findall(r'g_[0-9a-f]{16}',raw):
                if gid in allowed and gid not in parents: parents.append(gid)
            payload={'experiment_type':'queen_shadow_scouts','parent_genome_ids':parents[:2]}
        return {'action':action,'reasoning_summary':reasoning,'payload':payload}

def _compact(evidence):
    # Sceptic receives {'evidence': original_packet, 'core_proposal': ...}; flatten the
    # original packet so it can verify parents, controls and bloodline state instead of
    # judging a proposal without its grounding evidence.
    base=evidence.get('evidence') if isinstance(evidence.get('evidence'),dict) else evidence
    keep=['identity','authority','run_id','generation','frozen','evidence_cutoff','entries','shadow_plans','capital_doctrine','reproduction_doctrine','bloodline_ecology','colony_drives','queen_experiment_mandate','candidate_parents']
    out={k:base.get(k) for k in keep if k in base}
    out['independent_opportunities']=base.get('independent_opportunities')
    nc=base.get('niche_candidates') or []
    out['niche_candidates']=nc[:8] if isinstance(nc,list) else nc
    ex=base.get('experience') or []
    out['experience']=ex[-4:] if isinstance(ex,list) else ex
    if 'core_proposal' in evidence: out['core_proposal']=evidence.get('core_proposal')
    return out

def prompt(role,evidence):
    actions={'core':['observe','hypothesis','request_experiment','explain','ask_for_data'],
             'sceptic':['accept_for_test','veto','request_more_evidence','identify_confounder']}[role]
    return f'''You are colony {role}. Survival means meeting evidence-defined performance targets.
You have advisory authority only. Never claim you executed anything.
{('Your job is to attack the Core proposal as UNTRUSTED. Look specifically for leakage, dependence, hindsight, regime shift, unsupported mechanism claims, and unnecessary complexity. For queen_shadow_scouts specifically: the scouts are prospective, shadow-only, capped at two per brood, cannot trade real capital or replace the population, and exist to gather evidence. Thin evidence alone is therefore NOT a reason to veto; accept_for_test when the design is falsifiable and parent ids are grounded. A stated hypothesis that offspring may outperform a parent is a testable hypothesis, NOT an unsupported claim. If the proposal names a prospective cutoff/control, minimum evidence, success rule and failure rule, do not say it lacks falsifiability. Veto only for a concrete design/confounding problem that remains after those controls. Historical failure of a broader selection plan is not by itself a confounder for a matched child-versus-own-parent prospective test; explain specifically how any confounder survives the same-candidate parent control before blocking the test.' if role=='sceptic' else 'Generate one grounded hypothesis or experiment. Prefer falsifiable, minimal tests. HUMAN MANDATE: when current_active_shadow_scouts is zero and candidate_parents exist from a bloodline with reproductive credit, your action MUST be request_experiment for queen_shadow_scouts using one or two exact candidate_parent genome ids from the SAME bloodline. Otherwise choose the most useful grounded action.')}
Return ONE JSON object only: action, reasoning_summary, payload. Keep reasoning_summary under 35 words and payload minimal.
For Sceptic reviews of queen_shadow_scouts: if action is veto, identify_confounder, or request_more_evidence, payload MUST include blocking_issue and evidence_field. blocking_issue must be one of parent_not_grounded, mixed_bloodline, post_birth_leakage, unmatched_control, insufficient_independence, missing_failure_rule, or other_concrete. Generic phrases such as 'unsupported', 'not falsifiable', or 'leakage' without a surviving concrete mechanism are INVALID.
Allowed actions: {actions}.
For a queen_shadow_scouts experiment, payload must contain experiment_type='queen_shadow_scouts' and parent_genome_ids with ONE or TWO ids copied exactly from candidate_parents. Parents in one brood MUST be from the same bloodline. Never invent a genome id. The mature colony has no fixed total size; bloodlines may expand independently when evidence and resource capacity justify it. Prefer a tiny falsifiable shadow brood over population changes.
Mechanism contract:\n{json.dumps(mechanism_packet(),separators=(',',':'))}\nEvidence packet:\n{json.dumps(_compact(evidence),separators=(',',':'),default=str)[:7000]}'''


def _validate_sceptic_specificity(msg,evidence):
    proposal=evidence.get('core_proposal') if isinstance(evidence,dict) else None
    if not isinstance(proposal,dict): return True,'ok'
    p=proposal.get('payload') or {}
    if p.get('experiment_type')!='queen_shadow_scouts': return True,'ok'
    action=msg.get('action')
    if action=='accept_for_test': return True,'ok'
    payload=msg.get('payload') or {}
    allowed={'parent_not_grounded','mixed_bloodline','post_birth_leakage','unmatched_control','insufficient_independence','missing_failure_rule','other_concrete'}
    if payload.get('blocking_issue') not in allowed: return False,'generic_sceptic_block'
    if not payload.get('evidence_field'): return False,'missing_sceptic_evidence_field'
    return True,'ok'

async def infer(role,evidence,model='olmo-3:7b',timeout=180):
    started=time.time()
    actions={'core':['observe','hypothesis','request_experiment','explain','ask_for_data'],
             'sceptic':['accept_for_test','veto','request_more_evidence','identify_confounder']}[role]
    schema={'type':'object','properties':{
      'action':{'type':'string','enum':actions},
      'reasoning_summary':{'type':'string','maxLength':300},
      'payload':{'type':'object'}},
      'required':['action','reasoning_summary','payload'],'additionalProperties':False}
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r=await c.post(OLLAMA,json={'model':model,'prompt':prompt(role,evidence),'stream':False,'format':schema,'think':False,'options':{'num_ctx':2048,'num_predict':384,'temperature':0.1}})
            r.raise_for_status(); msg=_decode(r.json()['response'],role,evidence)
        ok,why=validate(msg,role)
        if ok and role=='core': ok,why=validate_grounding(msg)
        if ok and role=='sceptic': ok,why=_validate_sceptic_specificity(msg,evidence)
        return {'ok':ok,'validation':why,'message':msg if ok else None,'seconds':round(time.time()-started,2)}
    except Exception as e:
        return {'ok':False,'validation':'inference_error','error':str(e)[:300],'seconds':round(time.time()-started,2)}

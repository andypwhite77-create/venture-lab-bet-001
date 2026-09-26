"""Asynchronous, fail-closed local Queen/Sceptic inference."""
import json,httpx,time
from colony.mind_contract import validate
from colony.mind_grounding import validate_grounding,mechanism_packet
OLLAMA='http://127.0.0.1:11434/api/generate'

def prompt(role,evidence):
    actions={'core':['observe','hypothesis','request_experiment','explain','ask_for_data'],
             'sceptic':['accept_for_test','veto','request_more_evidence','identify_confounder']}[role]
    return f'''You are colony {role}. Survival means meeting evidence-defined performance targets.
You have advisory authority only. Never claim you executed anything.
{('Your job is to attack the Core proposal as UNTRUSTED. Look specifically for leakage, dependence, hindsight, regime shift, unsupported mechanism claims, and unnecessary complexity. Do not imitate its wording or action. You are rewarded for finding reasons an attractive idea could fail.' if role=='sceptic' else 'Generate one grounded hypothesis or experiment. Prefer falsifiable, minimal tests.')}
Return ONE JSON object only: action, reasoning_summary, payload.
Allowed actions: {actions}.
Mechanism contract:\n{json.dumps(mechanism_packet(),separators=(',',':'))}\nEvidence packet:\n{json.dumps(evidence,separators=(',',':'))[:12000]}'''

async def infer(role,evidence,model='olmo-3:7b',timeout=180):
    started=time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r=await c.post(OLLAMA,json={'model':model,'prompt':prompt(role,evidence),'stream':False,'format':'json','options':{'num_ctx':4096,'temperature':0.2}})
            r.raise_for_status(); msg=json.loads(r.json()['response'])
        ok,why=validate(msg,role)
        if ok and role=='core': ok,why=validate_grounding(msg)
        return {'ok':ok,'validation':why,'message':msg if ok else None,'seconds':round(time.time()-started,2)}
    except Exception as e:
        return {'ok':False,'validation':'inference_error','error':str(e)[:300],'seconds':round(time.time()-started,2)}

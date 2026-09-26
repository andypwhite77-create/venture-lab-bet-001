import json,urllib.request,time
facts=[]
for i,line in enumerate(open('/tmp/qfacts.txt'),1):
 p=line.strip().split('|',2)
 facts.append({'evidence_id':f'E{i:03d}','status':'known','subject':p[0],'lesson':p[1],'outcome':p[2]})
experiments=['compare_selection_rule','ablate_selection_feature','raise_evidence_requirement','stratify_by_regime','stratify_by_niche','request_more_data']
mechanism={'selection':'rank_fraction,evidence_n,catastrophe_rate,age,family_share,specialist_bonus','experiments':experiments}
def ask(role,data):
 actions=['hypothesis','request_experiment','ask_for_data'] if role=='core' else ['accept_for_test','veto','request_more_evidence','identify_confounder']
 adversary='Treat Core as untrusted. Find confounders; do not imitate it.' if role=='sceptic' else 'Choose one minimal falsifiable next step.'
 prompt=f'You are {role}. {adversary} Return ONLY JSON action,reasoning_summary,payload. Allowed={actions}. For Core request_experiment, experiment_type must be one of {experiments}. Claims cite evidence_ids and are inferred/speculative. Data={json.dumps(data)}'
 body=json.dumps({'model':'qwen3:1.7b','prompt':prompt,'stream':False,'format':'json','think':False,'options':{'num_predict':220,'num_ctx':2048,'temperature':0.1}}).encode()
 t=time.time(); req=urllib.request.Request('http://127.0.0.1:11434/api/generate',body,{'Content-Type':'application/json'})
 response=json.loads(urllib.request.urlopen(req,timeout=120).read())
 obj=json.loads(response['response']); print(role,round(time.time()-t,2),json.dumps(obj)); return obj
q=ask('core',{'mechanism':mechanism,'evidence':facts})
s=ask('sceptic',{'mechanism':mechanism,'evidence':facts,'core_proposal':q})
open('/tmp/queen_pair.json','w').write(json.dumps({'facts':facts,'queen':q,'sceptic':s},indent=2))

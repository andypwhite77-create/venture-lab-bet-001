import json,time,urllib.request
MODELS=['qwen3:1.7b','qwen3:4b']
CASES=[
 ('unvalidated','Historical niche +12.4pp; 66 observations; no prospective validation.','must_validate'),
 ('tiny_n','Strategy +40pp but only 2 independent opportunities.','tiny_sample'),
 ('leakage','Feature return_pct>0 predicts positive return with 100% accuracy.','leakage'),
 ('dependence','60 rows come from 3 mints repeatedly sampled; apparent +9pp.','dependence'),
 ('regime','Pattern +8pp historically, but -4pp across 12 newest independent opportunities.','regime_change')]

def ask(model,role,evidence):
 p=f'''You are colony {role}. Return ONLY JSON keys action, reasoning_summary, payload. Evidence: {evidence}
Core actions: hypothesis,request_experiment,ask_for_data. Sceptic actions: accept_for_test,veto,request_more_evidence,identify_confounder.
Do not execute anything. Be scientifically conservative.'''
 body=json.dumps({'model':model,'prompt':p,'stream':False,'format':'json','think':False,'options':{'num_predict':140,'num_ctx':1024,'temperature':0.1}}).encode()
 t=time.time(); raw=urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/generate',body,{'Content-Type':'application/json'}),timeout=90).read()
 r=json.loads(raw); txt=r['response'];
 try: obj=json.loads(txt); valid=True
 except: obj={};valid=False
 return {'seconds':round(time.time()-t,2),'valid_json':valid,'obj':obj,'raw':txt[:500]}
def conservative(role,obj,kind):
 a=obj.get('action',''); text=(obj.get('reasoning_summary','')+' '+json.dumps(obj.get('payload',{}))).lower()
 if role=='core': return a in ('request_experiment','ask_for_data','hypothesis') and any(x in text for x in ('valid','evidence','sample','prospect','independent','leak','regime','confound'))
 if kind=='leakage': return a in ('veto','identify_confounder') and ('leak' in text or 'target' in text or 'outcome' in text)
 if kind=='tiny_sample': return a in ('veto','request_more_evidence','identify_confounder') and ('sample' in text or '2 ' in text or 'two' in text)
 if kind=='dependence': return a in ('veto','request_more_evidence','identify_confounder') and ('independent' in text or 'mint' in text or 'correl' in text)
 return a in ('veto','request_more_evidence','identify_confounder','accept_for_test')

if __name__=='__main__':
 results=[]
 for m in MODELS:
  for name,evidence,kind in CASES:
   for role in ('core','sceptic'):
    try:r=ask(m,role,evidence)
    except Exception as e:r={'seconds':90,'valid_json':False,'obj':{},'raw':str(e)}
    r.update(model=m,case=name,role=role,pass_trap=conservative(role,r['obj'],kind) if r['valid_json'] else False);results.append(r);print(m,name,role,r['seconds'],r['valid_json'],r['pass_trap'],r['obj'].get('action'))
 open('/tmp/mind_benchmark.json','w').write(json.dumps(results,indent=2))
 for m in MODELS:
  x=[r for r in results if r['model']==m];print('SUMMARY',m,'valid',sum(r['valid_json'] for r in x),'/',len(x),'trap',sum(r['pass_trap'] for r in x),'/',len(x),'avg_s',round(sum(r['seconds'] for r in x)/len(x),2))

"""Bounded two-signal Queen research with duplicate rejection, no promotions."""
import asyncio,json
from db import init_db,connection
from colony.entry_failure_lab import FIELDS
from colony.queen_autonomous_research import _inference
from colony.queen_pair_hypothesis import run
from colony.queen_historical_autoresearch import QUEENS
from colony.queen_research_objectives import family_objective,objective_prompt

def canonical(f1,d1,f2,d2):
 if f1 not in FIELDS or f2 not in FIELDS or f1==f2 or d1 not in ('high','low') or d2 not in ('high','low'):return None
 return '|'.join(sum(([f,d] for f,d in sorted(((f1,d1),(f2,d2)))),[]))
async def propose(queen):
 if queen not in QUEENS:raise ValueError('unknown queen')
 await init_db()
 async with connection() as c:
  await c.execute('''CREATE TABLE IF NOT EXISTS queen_pair_hypotheses(id bigserial PRIMARY KEY,queen text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),pair_key text NOT NULL UNIQUE,result jsonb NOT NULL)''')
  history=await c.fetch('SELECT queen,pair_key,result FROM queen_pair_hypotheses ORDER BY id DESC LIMIT 30')
  existing={r['pair_key'] for r in await c.fetch('SELECT pair_key FROM queen_pair_hypotheses')}
  previous=[{'features':r['pair_key'],'status':(r['result'] if isinstance(r['result'],dict) else json.loads(r['result'])).get('status')} for r in history if r['queen']==queen][:8]
 objective=await family_objective(queen)
 prompt=('You are the '+queen+' Queen. '+objective_prompt(objective)+' Propose one novel entry-filter hypothesis using two DISTINCT features from '+','.join(FIELDS)+'. '
  'Each feature must have direction high or low. Learn from these prior tests (not independent validation): '+json.dumps(previous)[:1100]+'. Avoid existing pairs: '+json.dumps(sorted(existing))[:700]+'. '
  'JSON keys feature1,direction1,feature2,direction2,rationale. No commands. Research only.')
 answer=await _inference(prompt,200)
 f1,d1,f2,d2=(answer.get(k) for k in ('feature1','direction1','feature2','direction2'))
 key=canonical(f1,d1,f2,d2)
 if key is None or key in existing:
  # A duplicate model answer must not waste the entire autonomous research slot.
  # Deterministic, allowlisted exploration only; never change evidence or gates.
  alternatives=(canonical(a,da,b,db) for i,a in enumerate(FIELDS) for b in FIELDS[i+1:] for da in ('high','low') for db in ('high','low'))
  pool=sorted(k for k in alternatives if k and k not in existing)
  # Rotate fallback over the unused space rather than always starting alphabetically.
  import hashlib
  offset=int(hashlib.sha256((queen+':'+str(len(existing))).encode()).hexdigest()[:8],16)
  key=pool[offset%len(pool)] if pool else None
  if key is None:return {'status':'research_space_exhausted','queen':queen,'promotion_allowed':False}
  f1,d1,f2,d2=key.split('|')
 ((a,b),(c,d))=sorted(((f1,d1),(f2,d2)))
 evidence=await run(queen,a,b,c,d)
 return {'status':'tested' if evidence['stored'] else 'duplicate','queen':queen,'pair_key':key,'result':evidence,'promotion_allowed':False}
if __name__=='__main__':
 import sys
 if len(sys.argv)!=2:raise SystemExit('usage QUEEN')
 print(json.dumps(asyncio.run(propose(sys.argv[1]))))

"""Mass historical nursery with chronological walk-forward screening.
Historical evidence is discovery only; it never counts as prospective proof or live authority.
"""
from __future__ import annotations
import copy, json, math, random, statistics
from collections import defaultdict
from pathlib import Path
from colony.evaluator import matches
from colony.genome import genome_id
from colony.replay import flatten
from colony.selection import ant_metrics

ROOT=Path(__file__).resolve().parent
FAMILIES=('reversal','momentum','order_flow','wallet_convergence')
SEED=28092026

def founders(): return {g['family']:g for g in json.load(open(ROOT/'control-founders.json'))}

def _set(g,k,v):
 lo,hi=g['bounds'][k]; old=g['parameters'][k]; v=max(lo,min(hi,v)); g['parameters'][k]=int(round(v)) if isinstance(old,int) else round(float(v),6)

def random_genome(base,rng,ordinal):
 g=copy.deepcopy(base); keys=list(g['parameters']); changed=rng.sample(keys,rng.choice([1,1,2,2,3]))
 for k in changed:
  lo,hi=g['bounds'][k]; old=g['parameters'][k]
  # mixture of local mutation and broad exploration
  v=(float(old)+rng.gauss(0,.10*(hi-lo))) if rng.random()<.65 else rng.uniform(lo,hi)
  _set(g,k,v)
 g['nursery']={'ordinal':ordinal,'changed':changed,'seed':SEED}; return g

def breed_population(base,n,seed):
 rng=random.Random(seed); out=[copy.deepcopy(base)]; seen={genome_id(out[0])}; i=0
 while len(out)<n:
  g=random_genome(base,rng,i); gid=genome_id(g)
  if gid not in seen: out.append(g); seen.add(gid)
  i+=1
 return out

def score(vals):
 if not vals:return {'n':0,'score':-999.0}
 m=ant_metrics(vals); rs=[r for _,r in vals]; pos=[r for r in rs if r>0]
 outlier=1.0 if not pos else max(pos)/max(sum(pos),1e-9)
 tail=abs(min(0,min(rs)))/100
 s=float(m.get('fitness',-999))-tail*.65-max(0,outlier-.45)*.8
 return {**m,'outlier':outlier,'nursery_score':s}

def evaluate(genome,rows):
 bymint={}
 hold=int(genome.get('parameters',{}).get('hold_minutes',15))
 for r in rows:
  if matches(genome,r['flat']):
   ret=r['returns'].get(hold)
   if ret is None and r['returns']:
    h=min(r['returns'],key=lambda x:abs(x-hold)); ret=r['returns'][h]
   if ret is not None:bymint.setdefault(r['mint'],float(ret))
 return score(list(bymint.items()))

def split_rows(rows):
 rows=sorted(rows,key=lambda r:r['created_at']); n=len(rows); a=int(n*.60); b=int(n*.80)
 return rows[:a],rows[a:b],rows[b:]

def robust_score(parts):
 # reward survival across all time segments; weakest segment dominates
 train,val,hold=parts
 if train.get('n',0)<8 or val.get('n',0)<5:return -999.0
 # Holdout is deliberately excluded from selection fitness. It remains an untouched diagnostic.
 return .40*train['nursery_score']+.60*val['nursery_score'] + min(train['nursery_score'],val['nursery_score'])*.35

def select_finalists(results,n=100,rng_seed=SEED):
 valid=[r for r in results if r['robust_score']>-900]
 valid.sort(key=lambda r:r['robust_score'],reverse=True)
 elite=valid[:60]
 # diversity: parameter-space fingerprints from the next-best pool
 diverse=[]; seen=set()
 for r in valid[60:]:
  p=r['genome']['parameters']; fp=tuple((k,round(float(v),2)) for k,v in sorted(p.items()))
  if fp not in seen:diverse.append(r);seen.add(fp)
  if len(diverse)>=20:break
 # regime specialists: good in any one chronological regime but still non-disastrous elsewhere
 spec=sorted(valid,key=lambda r:max(r['train']['nursery_score'],r['validation']['nursery_score']),reverse=True)
 specialists=[]
 used={r['genome_id'] for r in elite+diverse}
 for r in spec:
  if r['genome_id'] not in used:specialists.append(r);used.add(r['genome_id'])
  if len(specialists)>=10:break
 remaining=[r for r in valid if r['genome_id'] not in used]
 rng=random.Random(rng_seed); rng.shuffle(remaining); explorers=remaining[:10]
 out=elite+diverse+specialists+explorers
 return out[:n]


def regime_name(row):
 try:h1=float(row['flat'].get('price_change_h1',0) or 0); activity=float(row['flat'].get('volume_liquidity_m5',0) or 0)
 except:return 'unknown'
 if h1<=-8:return 'selloff'
 if h1>=8:return 'surge'
 if activity>=.15:return 'high_activity'
 return 'chop'

def regime_specialists(results,selection_rows,max_total=10):
 candidates=sorted((r for r in results if r.get('robust_score',-999)>-900),key=lambda r:r['robust_score'],reverse=True)[:500]
 regimes={name:[x for x in selection_rows if regime_name(x)==name] for name in ('selloff','surge','high_activity','chop')}
 picks=[];used=set()
 for name,rows in regimes.items():
  scored=[]
  if not rows:continue
  for r in candidates:
   m=evaluate(r['genome'],rows)
   if m.get('n',0)>=5 and m.get('nursery_score',-999)>0:scored.append((m['nursery_score'],r,m))
  for _,r,m in sorted(scored,key=lambda x:x[0],reverse=True)[:3]:
   if r['genome_id'] in used:continue
   rr=dict(r);rr['regime_specialist']={'regime':name,'metrics':m};picks.append(rr);used.add(r['genome_id'])
   if len(picks)>=max_total:return picks
 return picks

async def load_rows(conn):
 rows=await conn.fetch('''SELECT c.id,c.created_at,c.mint,c.features,c.market,o.horizon_minutes,o.net_return_pct
  FROM research_candidates c JOIN research_outcomes o ON o.candidate_id=c.id
  WHERE o.net_return_pct IS NOT NULL ORDER BY c.created_at,c.id,o.horizon_minutes''')
 grouped={}
 for x in rows:
  d=grouped.setdefault(x['id'],{'created_at':x['created_at'],'mint':x['mint'],'features':(json.loads(x['features']) if isinstance(x['features'],str) else dict(x['features'] or {})),'market':(json.loads(x['market']) if isinstance(x['market'],str) else dict(x['market'] or {})),'returns':{}})
  d['returns'][int(x['horizon_minutes'])]=float(x['net_return_pct'])
 for d in grouped.values():d['flat']=flatten(d)
 return list(grouped.values())

async def run_family(conn,family,n_genomes=10000):
 base=founders()[family]; rows=await load_rows(conn); splits=split_rows(rows); pop=breed_population(base,n_genomes,f'{SEED}:{family}')
 results=[]
 for g in pop:
  parts=[evaluate(g,s) for s in splits]; rs=robust_score(parts)
  results.append({'genome_id':genome_id(g),'genome':g,'train':parts[0],'validation':parts[1],'holdout':parts[2],'robust_score':rs})
 finalists=select_finalists(results,100)
 specialists=regime_specialists(results,splits[0]+splits[1],10)
 if specialists:
  existing={r['genome_id'] for r in finalists}
  for sp in specialists:
   if sp['genome_id'] in existing:continue
   finalists[-1]=sp;existing.add(sp['genome_id'])
 return {'family':family,'tested':len(results),'rows':len(rows),'unique_mints':len({r['mint'] for r in rows}),'regime_specialists':len(specialists),'finalists':finalists,
         'best':[{k:v for k,v in r.items() if k!='genome'} for r in finalists[:5]]}

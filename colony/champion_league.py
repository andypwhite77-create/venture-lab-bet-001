"""Champion/challenger league.

Five distinct incumbent elites are the production research benchmark. Everyone else
competes in qualification. Spartan Arena is deliberately public/breeding-visible
historical comparison; a separate sealed Spartan exam remains untouched. Promotion
also requires prospective evidence, so a backtest alone cannot displace an elite.
"""
from __future__ import annotations
import hashlib,json,math,statistics,os
from datetime import datetime,timezone
from colony.evaluator import matches
from colony.forward import eligible
from colony.historical_nursery import sampled_path_return_pct
from colony.qualification_corpus import load_rows, sync as sync_corpus
from colony.paper_economics import TARGET_STAKE_GBP,adjusted_return_pct,measured_roundtrip_network_fee_sol,sol_gbp_rate
from colony.queen_roles import BREEDING_QUEEN

FOUNDER_ELITES=(
 'g_1f1774b3212a8863','g_b87af3b86a866981','g_bd729464d0b52699',
 'g_d20b45ea6d9be79a','g_b14e95af529a77d9')
MIN_FORWARD_EVENTS=25
MIN_FORWARD_DAYS=3
PROMOTION_COOLDOWN_SECONDS=int(os.getenv('CHAMPION_PROMOTION_COOLDOWN_SECONDS','259200'))
MAX_QUALIFICATION_DAYS=int(os.getenv('CHAMPION_MAX_QUALIFICATION_DAYS','21'))
MAX_QUALIFIERS_PER_BEHAVIOUR=int(os.getenv('CHAMPION_MAX_QUALIFIERS_PER_BEHAVIOUR','2'))
MIN_PROMOTION_WIN_RATE=float(os.getenv('CHAMPION_MIN_PROMOTION_WIN_RATE','0.55'))
MAX_PROMOTION_SINGLE_LOSS_PCT=float(os.getenv('CHAMPION_MAX_PROMOTION_SINGLE_LOSS_PCT','-25'))
MIN_PROMOTION_MEDIAN_PCT=float(os.getenv('CHAMPION_MIN_PROMOTION_MEDIAN_PCT','0.25'))
MIN_PROMOTION_POSITIVE_DAY_RATE=float(os.getenv('CHAMPION_MIN_PROMOTION_POSITIVE_DAY_RATE','0.60'))

def _cooldown_remaining(last_promotion,now=None,cooldown_seconds=PROMOTION_COOLDOWN_SECONDS):
 if not last_promotion:return 0
 now=now or datetime.now(timezone.utc)
 return max(0,int(cooldown_seconds-(now-last_promotion).total_seconds()))

def _retirement_reason(age_days,forward_n,total_score,worst_incumbent_total):
 if float(age_days)<MAX_QUALIFICATION_DAYS:return None
 if int(forward_n)<MIN_FORWARD_EVENTS:return 'training_budget_expired_insufficient_forward_evidence'
 if worst_incumbent_total is not None and (total_score is None or float(total_score)<=float(worst_incumbent_total)):
  return 'training_budget_expired_below_incumbent'
 return None

def _cap_qualification_behaviours(quals,cap=MAX_QUALIFIERS_PER_BEHAVIOUR):
 counts={};keep=[];retire=[]
 for q in quals:
  sig=q.get('sig')
  n=counts.get(sig,0)
  if n<int(cap):
   counts[sig]=n+1;keep.append(q)
  else:
   retire.append(q)
 return keep,retire

async def ensure_schema(c):
 await c.execute("""CREATE TABLE IF NOT EXISTS champion_league(
   genome_id TEXT PRIMARY KEY,family TEXT NOT NULL,genome JSONB NOT NULL,source TEXT NOT NULL,
   pool TEXT NOT NULL CHECK(pool IN ('elite','qualification')),elite_slot INT,
   enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(),promoted_at TIMESTAMPTZ,
   prospective_after_candidate BIGINT NOT NULL DEFAULT 0,behaviour_signature TEXT,
   arena_score DOUBLE PRECISION,forward_score DOUBLE PRECISION,total_score DOUBLE PRECISION,
   qualification_rank INT,active BOOLEAN NOT NULL DEFAULT true,retired_at TIMESTAMPTZ,retirement_reason TEXT,
   arena_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
   forward_stats JSONB NOT NULL DEFAULT '{}'::jsonb,notes JSONB NOT NULL DEFAULT '{}'::jsonb,
   updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
 ALTER TABLE champion_league ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT true;
 ALTER TABLE champion_league ADD COLUMN IF NOT EXISTS retired_at TIMESTAMPTZ;
 ALTER TABLE champion_league ADD COLUMN IF NOT EXISTS retirement_reason TEXT;
 CREATE UNIQUE INDEX IF NOT EXISTS champion_elite_slot ON champion_league(elite_slot) WHERE pool='elite';
 CREATE TABLE IF NOT EXISTS champion_paper_progress(
   id INT PRIMARY KEY CHECK(id=1),last_candidate_id BIGINT NOT NULL DEFAULT 0,
   initialized_at TIMESTAMPTZ,updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
 INSERT INTO champion_paper_progress(id) VALUES(1) ON CONFLICT DO NOTHING;
 CREATE TABLE IF NOT EXISTS champion_paper_entries(
   id BIGSERIAL PRIMARY KEY,genome_id TEXT NOT NULL REFERENCES champion_league(genome_id) ON DELETE CASCADE,
   candidate_id BIGINT NOT NULL,mint TEXT NOT NULL,observed_at TIMESTAMPTZ NOT NULL,
   hold_minutes INT NOT NULL,stake_gbp DOUBLE PRECISION NOT NULL DEFAULT 25,
   created_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(genome_id,candidate_id));
 CREATE INDEX IF NOT EXISTS champion_paper_genome_time ON champion_paper_entries(genome_id,observed_at);""")

def _json(v):
 if isinstance(v,str):
  try:return json.loads(v)
  except Exception:return {}
 return dict(v or {})

def _score(vals):
 vals=[float(x) for x in vals if x is not None]
 if not vals:return {'n':0,'mean':None,'median':None,'win_rate':None,'worst':None,'best':None,'lcb':None,'score':None}
 n=len(vals);mean=statistics.fmean(vals);med=statistics.median(vals);sd=statistics.stdev(vals) if n>1 else abs(mean)
 lcb=mean-1.2816*sd/math.sqrt(max(1,n));win=sum(x>0 for x in vals)/n
 # Conservative, percentage-point scale: downside-aware lower bound dominates.
 score=lcb+.25*med+1.5*(win-.5)
 return {'n':n,'mean':mean,'median':med,'win_rate':win,'worst':min(vals),'best':max(vals),'lcb':lcb,'score':score}

async def seed_founders(c):
 await ensure_schema(c); cutoff=int(await c.fetchval('SELECT coalesce(max(id),0) FROM research_candidates') or 0)
 seeded=[]; existing_elites=int(await c.fetchval("SELECT count(*) FROM champion_league WHERE pool='elite'") or 0)
 if existing_elites==0:
  for slot,gid in enumerate(FOUNDER_ELITES,1):
   r=await c.fetchrow("SELECT genome FROM reversal_tournament_ants WHERE genome_id=$1 ORDER BY born_at DESC LIMIT 1",gid)
   if not r:continue
   g=_json(r['genome'])
   await c.execute("""INSERT INTO champion_league(genome_id,family,genome,source,pool,elite_slot,prospective_after_candidate,promoted_at,notes)
     VALUES($1,'reversal',$2::jsonb,'reversal_founder','elite',$3,$4,now(),$5::jsonb)
     ON CONFLICT(genome_id) DO NOTHING""",
     gid,json.dumps(g),slot,cutoff,json.dumps({'founder':True,'selection':'top distinct five-day forward reversal behaviour'}))
   seeded.append(gid)
 else:
  seeded=[r['genome_id'] for r in await c.fetch("SELECT genome_id FROM champion_league WHERE pool='elite' ORDER BY elite_slot")]
 # Every reversal genome that actually traded joins qualification unless it is elite.
 rows=await c.fetch("""SELECT DISTINCT ON(a.genome_id) a.genome_id,a.genome FROM reversal_tournament_ants a
   JOIN reversal_tournament_entries e USING(run_id,genome_id) ORDER BY a.genome_id,a.born_at DESC""")
 for r in rows:
  gid=r['genome_id']
  if gid in FOUNDER_ELITES:continue
  await c.execute("""INSERT INTO champion_league(genome_id,family,genome,source,pool,prospective_after_candidate)
    VALUES($1,'reversal',$2::jsonb,'reversal_tournament','qualification',$3)
    ON CONFLICT(genome_id) DO NOTHING""",gid,json.dumps(_json(r['genome'])),cutoff)
 # Existing designed/reference candidates also belong in qualification.
 rows=await c.fetch("SELECT genome_id,family,genome,source FROM live_ant_registry WHERE live_candidate=true")
 for r in rows:
  if r['genome_id'] in FOUNDER_ELITES:continue
  await c.execute("""INSERT INTO champion_league(genome_id,family,genome,source,pool,prospective_after_candidate)
    VALUES($1,$2,$3::jsonb,$4,'qualification',$5) ON CONFLICT(genome_id) DO NOTHING""",
    r['genome_id'],r['family'],json.dumps(_json(r['genome'])),r['source'],cutoff)
 return {'elite':seeded,'qualification':await c.fetchval("SELECT count(*) FROM champion_league WHERE pool='qualification'")}

async def enroll_queen_top2(c,finalists,campaign):
 await ensure_schema(c);cutoff=int(await c.fetchval('SELECT coalesce(max(id),0) FROM research_candidates') or 0)
 ranked=sorted(finalists or [],key=lambda x:float(x.get('selection_score',-1e9)),reverse=True)
 added=[]
 for x in ranked:
  gid=x.get('genome_id');g=x.get('genome') or {}
  if not gid or not g or gid in added:continue
  await c.execute("""INSERT INTO champion_league(genome_id,family,genome,source,pool,prospective_after_candidate,notes)
    VALUES($1,'queen_pattern',$2::jsonb,'queen','qualification',$3,$4::jsonb)
    ON CONFLICT(genome_id) DO UPDATE SET notes=champion_league.notes||excluded.notes,updated_at=now()""",
    gid,json.dumps(g),cutoff,json.dumps({'queen_campaign':int(campaign),'queen_selection_score':x.get('selection_score')}))
  added.append(gid)
  if len(added)>=int(BREEDING_QUEEN['qualification_handoff']):break
 return {'campaign':campaign,'enrolled':added}

async def paper_run_once(c,limit=1000):
 await ensure_schema(c);p=await c.fetchrow('SELECT * FROM champion_paper_progress WHERE id=1 FOR UPDATE')
 last=int(p['last_candidate_id'] or 0)
 if not p['initialized_at']:
  last=int(await c.fetchval('SELECT coalesce(max(id),0) FROM research_candidates') or 0)
  await c.execute('UPDATE champion_paper_progress SET last_candidate_id=$1,initialized_at=now(),updated_at=now() WHERE id=1',last)
 rows=await c.fetch("SELECT id,created_at,mint,features,market FROM research_candidates WHERE id>$1 ORDER BY id LIMIT $2",last,int(limit))
 ants=await c.fetch("SELECT genome_id,genome,prospective_after_candidate FROM champion_league WHERE active=true ORDER BY genome_id")
 inserted=0
 for rr0 in rows:
  rr=dict(rr0)
  for a in ants:
   if rr['id']<=int(a['prospective_after_candidate'] or 0):continue
   g=_json(a['genome']);hold=int(g.get('parameters',{}).get('hold_minutes',15))
   if not eligible(g,rr,None):continue
   res=await c.execute("""INSERT INTO champion_paper_entries(genome_id,candidate_id,mint,observed_at,hold_minutes,stake_gbp)
     VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING""",a['genome_id'],rr['id'],rr['mint'],rr['created_at'],hold,TARGET_STAKE_GBP)
   inserted+=int(res.endswith('1'))
 if rows:await c.execute('UPDATE champion_paper_progress SET last_candidate_id=$1,updated_at=now() WHERE id=1',rows[-1]['id'])
 return {'ants':len(ants),'candidates':len(rows),'entries':inserted,'last_candidate_id':rows[-1]['id'] if rows else last}

def _behaviour_signature(events,g):
 prm=g.get('parameters',{})
 raw=repr((tuple(events),int(prm.get('hold_minutes',15)),prm.get('stop_loss_pct'),prm.get('take_profit_pct')))
 return hashlib.sha1(raw.encode()).hexdigest()[:20]

async def _forward_for(c,gid,fixed_gbp):
 vals=[];days=set();seen=set();by_day={}
 # Existing Reversal tournament evidence is genuine forward paper and remains valuable.
 rows=await c.fetch("""SELECT e.candidate_id,e.observed_at,e.hold_minutes,o.net_return_pct
   FROM reversal_tournament_entries e JOIN research_outcomes o ON o.candidate_id=e.candidate_id AND o.horizon_minutes=e.hold_minutes
   WHERE e.genome_id=$1 AND o.measured_at>=e.observed_at ORDER BY e.observed_at""",gid)
 for r in rows:
  key=('r',r['candidate_id'])
  if key in seen:continue
  seen.add(key);v=float(r['net_return_pct']);vals.append(v);d=r['observed_at'].date();days.add(d);by_day.setdefault(d,[]).append(v)
 rows=await c.fetch("""SELECT e.candidate_id,e.observed_at,e.stake_gbp,o.net_return_pct
   FROM champion_paper_entries e JOIN research_outcomes o ON o.candidate_id=e.candidate_id AND o.horizon_minutes=e.hold_minutes
   WHERE e.genome_id=$1 AND o.measured_at>=e.observed_at ORDER BY e.observed_at""",gid)
 for r in rows:
  key=('c',r['candidate_id'])
  if key in seen:continue
  seen.add(key);v=adjusted_return_pct(float(r['net_return_pct']),float(r['stake_gbp']),fixed_gbp);vals.append(v);d=r['observed_at'].date();days.add(d);by_day.setdefault(d,[]).append(v)
 s=_score(vals);s['days']=len(days)
 day_means=[statistics.fmean(v) for v in by_day.values() if v]
 s['positive_day_rate']=(sum(x>0 for x in day_means)/len(day_means)) if day_means else None
 s['worst_day_mean']=min(day_means) if day_means else None
 return s

async def refresh_rankings(c,allow_promotion=True):
 await ensure_schema(c);await sync_corpus(c);rows=await load_rows(c);fee=await measured_roundtrip_network_fee_sol(c);rate,_=sol_gbp_rate();fixed=fee*rate
 ants=await c.fetch('SELECT * FROM champion_league WHERE active=true ORDER BY genome_id');computed=[]
 for a in ants:
  g=_json(a['genome']);vals=[];events=[];seen=set()
  for r in rows:
   if r['mint'] in seen or not matches(g,r.get('flat') or {}):continue
   ret=sampled_path_return_pct(g,r['returns'])
   if ret is None:continue
   seen.add(r['mint']);events.append(r['mint']);vals.append(float(ret))
  arena=_score(vals);forward=await _forward_for(c,a['genome_id'],fixed)
  total=None
  if arena['score'] is not None:
   total=arena['score'] if forward['score'] is None else .55*arena['score']+.45*forward['score']
  sig=_behaviour_signature(events,g)
  computed.append({'genome_id':a['genome_id'],'pool':a['pool'],'elite_slot':a['elite_slot'],'arena':arena,'forward':forward,'total':total,'sig':sig})
 for x in computed:
  await c.execute("""UPDATE champion_league SET arena_score=$2,forward_score=$3,total_score=$4,behaviour_signature=$5,
    arena_stats=$6::jsonb,forward_stats=$7::jsonb,updated_at=now() WHERE genome_id=$1""",x['genome_id'],x['arena']['score'],x['forward']['score'],x['total'],x['sig'],json.dumps(x['arena']),json.dumps(x['forward']))
 quals=sorted([x for x in computed if x['pool']=='qualification'],key=lambda x:(x['total'] is not None,x['total'] or -1e9),reverse=True)
 quals,duplicate_retire=_cap_qualification_behaviours(quals)
 for q in duplicate_retire:
  await c.execute("UPDATE champion_league SET active=false,retired_at=now(),retirement_reason='duplicate_behaviour_cap',qualification_rank=NULL,updated_at=now() WHERE genome_id=$1",q['genome_id'])
 elites=[x for x in computed if x['pool']=='elite'];promotion=None
 last_promotion=await c.fetchval("SELECT max(promoted_at) FROM champion_league WHERE source<>'reversal_founder' AND promoted_at IS NOT NULL")
 promotion_cooldown_remaining=_cooldown_remaining(last_promotion)
 # Expire challengers that have consumed three weeks of research budget without
 # establishing a credible incumbent-beating record. Evidence is retained in-place.
 worst_total=min((x['total'] for x in elites if x['total'] is not None),default=None)
 retired=[{'genome_id':q['genome_id'],'reason':'duplicate_behaviour_cap','age_days':None,'forward_n':q['forward'].get('n',0),'total_score':q['total']} for q in duplicate_retire]
 now=datetime.now(timezone.utc)
 for q in quals:
  row=next((a for a in ants if a['genome_id']==q['genome_id']),None)
  if not row: continue
  age_days=max(0.0,(now-row['enrolled_at']).total_seconds()/86400.0)
  if age_days < MAX_QUALIFICATION_DAYS: continue
  f=q['forward']; reason=_retirement_reason(age_days,f.get('n',0),q['total'],worst_total)
  if reason:
   await c.execute("UPDATE champion_league SET active=false,retired_at=now(),retirement_reason=$2,qualification_rank=NULL,updated_at=now() WHERE genome_id=$1",q['genome_id'],reason)
   retired.append({'genome_id':q['genome_id'],'reason':reason,'age_days':round(age_days,2),'forward_n':f.get('n',0),'total_score':q['total']})
 quals=[q for q in quals if q['genome_id'] not in {x['genome_id'] for x in retired}]
 for i,x in enumerate(quals,1):await c.execute('UPDATE champion_league SET qualification_rank=$2 WHERE genome_id=$1',x['genome_id'],i)
 if allow_promotion and len(elites)>=1 and promotion_cooldown_remaining==0:
  worst=min(elites,key=lambda x:x['total'] if x['total'] is not None else -1e9);elite_sigs={x['sig'] for x in elites}
  for q in quals:
   f=q['forward'];a=q['arena']
   if q['sig'] in elite_sigs or f['n']<MIN_FORWARD_EVENTS or f.get('days',0)<MIN_FORWARD_DAYS:continue
   if q['total'] is None or worst['total'] is None:continue
   if a['score'] is None or worst['arena']['score'] is None or a['score']<=worst['arena']['score']:continue
   if f['score'] is None or worst['forward']['score'] is None or f['score']<=worst['forward']['score']:continue
   if (f.get('win_rate') is None or f['win_rate']<MIN_PROMOTION_WIN_RATE
       or f.get('worst') is None or f['worst']<MAX_PROMOTION_SINGLE_LOSS_PCT
       or f.get('median') is None or f['median']<MIN_PROMOTION_MEDIAN_PCT
       or f.get('positive_day_rate') is None or f['positive_day_rate']<MIN_PROMOTION_POSITIVE_DAY_RATE):continue
   slot=worst['elite_slot']
   async with c.transaction():
    await c.execute("UPDATE champion_league SET pool='qualification',elite_slot=NULL,qualification_rank=NULL,updated_at=now() WHERE genome_id=$1",worst['genome_id'])
    await c.execute("UPDATE champion_league SET pool='elite',elite_slot=$2,promoted_at=now(),qualification_rank=NULL,updated_at=now() WHERE genome_id=$1",q['genome_id'],slot)
   promotion={'in':q['genome_id'],'out':worst['genome_id'],'slot':slot,'challenger_total':q['total'],'incumbent_total':worst['total']};break
 return {'elite':[x['genome_id'] for x in sorted(elites,key=lambda z:z['elite_slot'] or 99)],'qualification_count':len(quals),'top_qualification':[{'genome_id':x['genome_id'],'total_score':x['total'],'arena_score':x['arena']['score'],'forward_score':x['forward']['score'],'forward_n':x['forward']['n'],'forward_days':x['forward'].get('days',0)} for x in quals[:10]],'promotion':promotion,'retired':retired,'max_qualification_days':MAX_QUALIFICATION_DAYS,'max_qualifiers_per_behaviour':MAX_QUALIFIERS_PER_BEHAVIOUR,'min_promotion_win_rate':MIN_PROMOTION_WIN_RATE,'max_promotion_single_loss_pct':MAX_PROMOTION_SINGLE_LOSS_PCT,'min_promotion_median_pct':MIN_PROMOTION_MEDIAN_PCT,'min_promotion_positive_day_rate':MIN_PROMOTION_POSITIVE_DAY_RATE,'promotion_cooldown_seconds':PROMOTION_COOLDOWN_SECONDS,'promotion_cooldown_remaining':promotion_cooldown_remaining}

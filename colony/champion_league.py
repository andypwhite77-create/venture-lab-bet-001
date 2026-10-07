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
CANARY_ROSTER_SIZE=max(1,int(os.getenv('CHAMPION_CANARY_ROSTER_SIZE','5')))
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
 ALTER TABLE champion_league ADD COLUMN IF NOT EXISTS canary_slot INT;
 ALTER TABLE champion_league ADD COLUMN IF NOT EXISTS canary_since TIMESTAMPTZ;
 ALTER TABLE champion_league ADD COLUMN IF NOT EXISTS canary_demoted_at TIMESTAMPTZ;
 CREATE UNIQUE INDEX IF NOT EXISTS champion_elite_slot ON champion_league(elite_slot) WHERE pool='elite';
 CREATE UNIQUE INDEX IF NOT EXISTS champion_canary_slot ON champion_league(canary_slot) WHERE canary_slot IS NOT NULL;
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


def _historical_priority(arena):
 """Research-priority tier from breeding-visible historical robustness only.

 This affects evidence-service order, never promotion eligibility or Spartan.
 """
 if not arena or arena.get('n',0)<20:return None
 mean=arena.get('mean'); med=arena.get('median'); win=arena.get('win_rate')
 worst=arena.get('worst'); lcb=arena.get('lcb')
 if None in (mean,med,win,worst,lcb) or lcb<=0:return None
 if mean>=4 and med>=2 and win>=.70 and worst>=-15:return 'A+'
 if mean>=2 and med>=.5 and win>=.60 and worst>=-30:return 'A'
 return None

def _priority_sort_key(row):
 notes=_json(row.get('notes'))
 tier=notes.get('historical_priority_tier')
 return (0 if tier=='A+' else 1 if tier=='A' else 2, row.get('genome_id',''))


def _passes_canary_paper_gate(x):
 f=x.get('forward') or {}
 return (int(f.get('n') or 0)>=MIN_FORWARD_EVENTS
         and int(f.get('days') or 0)>=MIN_FORWARD_DAYS
         and f.get('win_rate') is not None and float(f['win_rate'])>=MIN_PROMOTION_WIN_RATE
         and f.get('worst') is not None and float(f['worst'])>=MAX_PROMOTION_SINGLE_LOSS_PCT
         and f.get('median') is not None and float(f['median'])>=MIN_PROMOTION_MEDIAN_PCT
         and f.get('positive_day_rate') is not None and float(f['positive_day_rate'])>=MIN_PROMOTION_POSITIVE_DAY_RATE
         and f.get('score') is not None and x.get('arena',{}).get('score') is not None
         and x.get('total') is not None)

def _canary_strength(x):
 f=x.get('forward') or {}
 return (float(f.get('score') if f.get('score') is not None else -1e99),
         float(x.get('total') if x.get('total') is not None else -1e99),
         float(x.get('arena',{}).get('score') if x.get('arena',{}).get('score') is not None else -1e99))

def _challenger_beats_canary(challenger,incumbent):
 if not _passes_canary_paper_gate(challenger): return False
 cf=challenger.get('forward') or {}; wf=incumbent.get('forward') or {}
 if cf.get('score') is None or challenger.get('total') is None or challenger.get('arena',{}).get('score') is None:return False
 if wf.get('score') is not None and float(cf['score'])<=float(wf['score']):return False
 if incumbent.get('total') is not None and float(challenger['total'])<=float(incumbent['total']):return False
 if incumbent.get('arena',{}).get('score') is not None and float(challenger['arena']['score'])<=float(incumbent['arena']['score']):return False
 return True

async def sync_canary_roster(c,computed,allow_rotation=True):
 """Maintain a fixed-size merit roster for real-money Canary signalling.

 Bootstrap uses incumbent research elites. Thereafter a challenger needs 25+ fresh
 paper trades, reliability gates and superior historical+forward evidence to evict
 the weakest Canary. At most one slot changes per maintenance tick.
 """
 byid={x['genome_id']:x for x in computed}
 rows=await c.fetch("SELECT genome_id,canary_slot,pool,elite_slot FROM champion_league WHERE active=true AND canary_slot IS NOT NULL ORDER BY canary_slot")
 # Remove slots outside a reduced configured roster.
 for r in rows:
  if int(r['canary_slot'])>CANARY_ROSTER_SIZE:
   await c.execute("UPDATE champion_league SET canary_slot=NULL,canary_demoted_at=now(),updated_at=now(),notes=notes||$2::jsonb WHERE genome_id=$1",
                   r['genome_id'],json.dumps({'canary_last_event':'configured_roster_shrink'}))
 rows=await c.fetch("SELECT genome_id,canary_slot,pool,elite_slot FROM champion_league WHERE active=true AND canary_slot IS NOT NULL ORDER BY canary_slot")
 occupied={int(r['canary_slot']) for r in rows}
 current_ids={r['genome_id'] for r in rows}
 # First deployment and later roster expansion: seed missing slots from existing elites,
 # then from the strongest paper-qualified challengers.
 missing=[i for i in range(1,CANARY_ROSTER_SIZE+1) if i not in occupied]
 if missing:
  seeds=sorted([x for x in computed if x['genome_id'] not in current_ids and x.get('pool')=='elite'],
               key=lambda x:(x.get('elite_slot') or 999))
  seeds += sorted([x for x in computed if x['genome_id'] not in current_ids and x.get('pool')!='elite' and _passes_canary_paper_gate(x)],
                  key=_canary_strength,reverse=True)
  for slot,x in zip(missing,seeds):
   await c.execute("UPDATE champion_league SET canary_slot=$2,canary_since=now(),canary_demoted_at=NULL,updated_at=now(),notes=notes||$3::jsonb WHERE genome_id=$1",
                   x['genome_id'],slot,json.dumps({'canary_last_event':'bootstrap_or_expand'}))
   current_ids.add(x['genome_id'])
 rows=await c.fetch("SELECT genome_id,canary_slot FROM champion_league WHERE active=true AND canary_slot IS NOT NULL ORDER BY canary_slot")
 roster=[byid[r['genome_id']] for r in rows if r['genome_id'] in byid]
 rotation=None
 if allow_rotation and len(roster)>=CANARY_ROSTER_SIZE:
  worst=min(roster,key=_canary_strength)
  other_sigs={x.get('sig') for x in roster if x['genome_id']!=worst['genome_id']}
  challengers=[x for x in computed if x['genome_id'] not in {r['genome_id'] for r in roster}
               and x.get('sig') not in other_sigs and _challenger_beats_canary(x,worst)]
  if challengers:
   challenger=max(challengers,key=_canary_strength)
   slot=int(await c.fetchval("SELECT canary_slot FROM champion_league WHERE genome_id=$1",worst['genome_id']))
   async with c.transaction():
    await c.execute("UPDATE champion_league SET canary_slot=NULL,canary_demoted_at=now(),updated_at=now(),notes=notes||$2::jsonb WHERE genome_id=$1",
                    worst['genome_id'],json.dumps({'canary_last_event':'demoted_by_upstart','canary_replaced_by':challenger['genome_id']}))
    await c.execute("UPDATE champion_league SET canary_slot=$2,canary_since=now(),canary_demoted_at=NULL,updated_at=now(),notes=notes||$3::jsonb WHERE genome_id=$1",
                    challenger['genome_id'],slot,json.dumps({'canary_last_event':'promoted_from_paper','canary_replaced':worst['genome_id']}))
   rotation={'in':challenger['genome_id'],'out':worst['genome_id'],'slot':slot,
             'challenger_forward_n':challenger['forward']['n'],
             'challenger_forward_score':challenger['forward']['score'],
             'incumbent_forward_score':worst['forward'].get('score')}
   rows=await c.fetch("SELECT genome_id,canary_slot FROM champion_league WHERE active=true AND canary_slot IS NOT NULL ORDER BY canary_slot")
 return {'size':CANARY_ROSTER_SIZE,'roster':[{'slot':int(r['canary_slot']),'genome_id':r['genome_id']} for r in rows],'rotation':rotation}

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
 ants=[dict(a) for a in await c.fetch("SELECT genome_id,genome,prospective_after_candidate,notes FROM champion_league WHERE active=true ORDER BY genome_id")]
 ants.sort(key=_priority_sort_key)
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
 priority_counts={'A+':0,'A':0}
 for a in ants:
  tier=_json(a.get('notes')).get('historical_priority_tier')
  if tier in priority_counts:priority_counts[tier]+=1
 return {'ants':len(ants),'candidates':len(rows),'entries':inserted,'last_candidate_id':rows[-1]['id'] if rows else last,'priority_ants':priority_counts}

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
  priority=_historical_priority(arena)
  computed.append({'genome_id':a['genome_id'],'pool':a['pool'],'elite_slot':a['elite_slot'],'arena':arena,'forward':forward,'total':total,'sig':sig,'historical_priority':priority})
 for x in computed:
  priority_note={'historical_priority_tier':x['historical_priority'],'historical_priority_basis':'breeding_visible_arena_v1'} if x['historical_priority'] else {'historical_priority_tier':None,'historical_priority_basis':'breeding_visible_arena_v1'}
  await c.execute("""UPDATE champion_league SET arena_score=$2,forward_score=$3,total_score=$4,behaviour_signature=$5,
    arena_stats=$6::jsonb,forward_stats=$7::jsonb,notes=notes||$8::jsonb,updated_at=now() WHERE genome_id=$1""",x['genome_id'],x['arena']['score'],x['forward']['score'],x['total'],x['sig'],json.dumps(x['arena']),json.dumps(x['forward']),json.dumps(priority_note))
 canary=await sync_canary_roster(c,computed,allow_rotation=allow_promotion)
 canary_ids={x['genome_id'] for x in canary['roster']}
 all_quals=sorted([x for x in computed if x['pool']=='qualification'],key=lambda x:(x['total'] is not None,x['total'] or -1e9),reverse=True)
 quals,duplicate_retire=_cap_qualification_behaviours(all_quals)
 protected_dupes=[q for q in duplicate_retire if q['genome_id'] in canary_ids]
 duplicate_retire=[q for q in duplicate_retire if q['genome_id'] not in canary_ids]
 quals=sorted(quals+protected_dupes,key=lambda x:(x['total'] is not None,x['total'] or -1e9),reverse=True)
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
  if q['genome_id'] in canary_ids: continue
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
 return {'elite':[x['genome_id'] for x in sorted(elites,key=lambda z:z['elite_slot'] or 99)],'canary':canary,'qualification_count':len(quals),'top_qualification':[{'genome_id':x['genome_id'],'total_score':x['total'],'arena_score':x['arena']['score'],'forward_score':x['forward']['score'],'forward_n':x['forward']['n'],'forward_days':x['forward'].get('days',0)} for x in quals[:10]],'historical_priority':[{'genome_id':x['genome_id'],'tier':x['historical_priority'],'arena_n':x['arena']['n'],'arena_mean':x['arena']['mean'],'arena_median':x['arena']['median'],'arena_win_rate':x['arena']['win_rate'],'arena_worst':x['arena']['worst']} for x in computed if x['historical_priority']], 'promotion':promotion,'retired':retired,'max_qualification_days':MAX_QUALIFICATION_DAYS,'max_qualifiers_per_behaviour':MAX_QUALIFIERS_PER_BEHAVIOUR,'min_promotion_win_rate':MIN_PROMOTION_WIN_RATE,'max_promotion_single_loss_pct':MAX_PROMOTION_SINGLE_LOSS_PCT,'min_promotion_median_pct':MIN_PROMOTION_MEDIAN_PCT,'min_promotion_positive_day_rate':MIN_PROMOTION_POSITIVE_DAY_RATE,'promotion_cooldown_seconds':PROMOTION_COOLDOWN_SECONDS,'promotion_cooldown_remaining':promotion_cooldown_remaining}

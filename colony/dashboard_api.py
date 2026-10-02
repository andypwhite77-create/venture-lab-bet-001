import json, os, time, urllib.request, asyncio
from db import connection
from colony.selection_state import snapshot as selection_snapshot
from colony.capital_shadow import snapshot as capital_shadow_snapshot
from colony.canary_wallet import snapshot as canary_wallet_snapshot
from colony.queen_scouts import summary as queen_scout_summary
from colony.biology_ecology import snapshot as biology_snapshot
from colony.drives import snapshot as drives_snapshot
from colony.paper_economics import TARGET_STAKE_GBP,measured_roundtrip_network_fee_sol,sol_gbp_rate
from colony.swarm_queen import latest as swarm_queen_latest
from colony.platform_governance import snapshot as platform_snapshot
_fx={'rate':None,'at':0}
def _sol_gbp():
 now=time.time()
 if _fx['rate'] is not None and now-_fx['at']<300:return _fx['rate']
 try:
  req=urllib.request.Request('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=gbp',headers={'x-cg-demo-api-key':os.getenv('COINGECKO_API_KEY','')})
  with urllib.request.urlopen(req,timeout=4) as r: rate=float(json.load(r)['solana']['gbp'])
  _fx.update(rate=rate,at=now);return rate
 except Exception:return _fx['rate']
async def _run(conn,run_id):
 ids=list(run_id) if isinstance(run_id,(list,tuple)) else [run_id]
 trades=await conn.fetch('''SELECT intent_id,created_at,mint,side,notional,status,reason,quote,entry_price,mark_price,gross_pnl,friction_cost,net_pnl,broadcast,execution_reality,friction_ratio,executable_edge_sol FROM colony_execution_ledger WHERE run_id=ANY($1::text[]) ORDER BY id DESC LIMIT 60''',ids)
 curve=await conn.fetch('''SELECT created_at,net_pnl,gross_pnl,friction_cost,quote FROM colony_execution_ledger WHERE run_id=ANY($1::text[]) AND net_pnl IS NOT NULL ORDER BY id''',ids)
 out=[]
 for r in trades:
  d=dict(r);q=d.pop('quote') or {};q=json.loads(q) if isinstance(q,str) else q;d['attribution']=q.get('attribution');out.append(d)

 summ=await conn.fetchrow("""SELECT count(*) n,count(*) FILTER(WHERE status='accepted') accepted,count(*) FILTER(WHERE status='rejected') rejected,coalesce(sum(net_pnl),0) net_pnl,avg(net_pnl) FILTER(WHERE net_pnl IS NOT NULL) avg_net FROM colony_execution_ledger WHERE run_id=ANY($1::text[])""",ids)
 curve_out=[]
 for x in curve:
  d=dict(x); q=d.pop('quote') or {}; q=json.loads(q) if isinstance(q,str) else q; d['family']=(q.get('attribution') or {}).get('family'); curve_out.append(d)
 return {'run_id':run_id,'summary':dict(summ),'trades':out,'curve':curve_out}
async def _snapshot_fresh():
 async with connection() as c:
  external=await _run(c,'paper-livequote-v1');native=await _run(c,['colony-native-v3-holdaware'])
  signals=await c.fetch('''SELECT id,created_at,mint,direction,confidence,reference_price FROM signal_events ORDER BY id DESC LIMIT 30''')
  genomes=await c.fetch("""SELECT family,count(DISTINCT genome_id) n FROM colony_forward_entries GROUP BY family ORDER BY family""")
  events=await c.fetch('''SELECT event_type,payload,created_at FROM colony_events ORDER BY id DESC LIMIT 25''')
  mind=await c.fetch("""SELECT run_id,observed_at,status,core,sceptic FROM colony_mind_journal ORDER BY id DESC LIMIT 12""")
  exps=await c.fetch('''SELECT experiment_type,status,created_at FROM colony_mind_experiments ORDER BY id DESC LIMIT 10''')
  lineage=await c.fetch("""SELECT s.id signal_id,f.family,count(DISTINCT f.genome_id) ants FROM signal_events s JOIN colony_forward_entries f ON f.mint=s.mint AND f.observed_at BETWEEN s.created_at-interval '30 minutes' AND s.created_at+interval '5 minutes' WHERE s.id IN (SELECT id FROM signal_events ORDER BY id DESC LIMIT 30) GROUP BY s.id,f.family ORDER BY s.id DESC,ants DESC""")
  fam=await c.fetch('''SELECT quote->'attribution'->>'family' family,count(*) trades,
   count(*) FILTER(WHERE net_pnl>0) wins,coalesce(sum(net_pnl),0) net
   FROM colony_execution_ledger WHERE run_id=ANY($1::text[]) GROUP BY 1 ORDER BY net DESC''',['colony-native-v3-holdaware'])
  # Current elite-training roster is separate from the frozen forward-run provenance above.
  elite=[]
  rr=await c.fetchrow("SELECT run_id,stage_size,stage_index,status FROM reversal_tournament_runs ORDER BY created_at DESC LIMIT 1")
  if rr:
   rc=await c.fetchrow('''SELECT count(*) FILTER(WHERE active) active,
      count(*) FILTER(WHERE active AND baseline) controls,
      count(*) FILTER(WHERE active AND NOT baseline AND cohort='historical_qualified') elites
      FROM reversal_tournament_ants WHERE run_id=$1''',rr['run_id'])
   elite.append({'family':'reversal',**dict(rc),'stage_size':rr['stage_size'],'stage_index':rr['stage_index'],'status':rr['status']})
  fruns=await c.fetch("SELECT DISTINCT ON(family) run_id,family,stage_size,stage_index,status FROM family_tournament_runs ORDER BY family,created_at DESC")
  for r in fruns:
   fc=await c.fetchrow('''SELECT count(*) FILTER(WHERE active) active,
      count(*) FILTER(WHERE active AND baseline) controls,
      count(*) FILTER(WHERE active AND NOT baseline AND cohort='historical_qualified') elites
      FROM family_tournament_ants WHERE run_id=$1''',r['run_id'])
   elite.append({'family':r['family'],**dict(fc),'stage_size':r['stage_size'],'stage_index':r['stage_index'],'status':r['status']})
  qrows=await c.fetch("SELECT family,count(*) waiting,max(historical_score) best_score FROM evolution_candidate_queue WHERE status='ready' GROUP BY family")
  qmap={r['family']:dict(r) for r in qrows}
  for e in elite:
   q=qmap.get(e['family'],{});e['challengers']=q.get('waiting',0);e['best_challenger_score']=q.get('best_score')
  accel=await c.fetchval("SELECT value FROM acceleration_state WHERE key='historical_nursery'")
  accel=json.loads(accel) if isinstance(accel,str) else (accel or {})
  current_mints=await c.fetchval('''SELECT count(DISTINCT c.mint) FROM research_candidates c
    WHERE EXISTS(SELECT 1 FROM research_outcomes o WHERE o.candidate_id=c.id AND o.net_return_pct IS NOT NULL)''')
  accel={'last_mints':int(accel.get('unique_mints',0)),'current_mints':int(current_mints or 0),
         'new_mints':max(0,int(current_mints or 0)-int(accel.get('unique_mints',0))),'trigger_at':25}
  rate=await asyncio.to_thread(_sol_gbp)
  econ_rate,_econ_source=sol_gbp_rate(); rate=rate if rate is not None else econ_rate
  families=[dict(x) for x in fam]
  for x in families:x['net_gbp']=float(x['net'])*rate if rate is not None else None
  fee_sol=await measured_roundtrip_network_fee_sol(c); fee_gbp=fee_sol*econ_rate
  stake_model={'stake_gbp':TARGET_STAKE_GBP,'roundtrip_network_fee_sol':fee_sol,'roundtrip_network_fee_gbp':fee_gbp,'fixed_fee_pct_at_stake':(fee_gbp/TARGET_STAKE_GBP*100.0 if TARGET_STAKE_GBP else None),'rate_source':_econ_source}
  health=await c.fetch("""SELECT DISTINCT ON(provider) provider,ok,observed_at,error,latency_ms FROM colony_provider_health ORDER BY provider,observed_at DESC""")
  health=[dict(x) for x in health]
  research=await c.fetch('''SELECT DISTINCT ON(family) family,created_at,tested_genomes,historical_rows,summary FROM historical_nursery_runs ORDER BY family,created_at DESC''')
  research=[dict(x) for x in research]
  payload={'external':external,'native':native,'sol_gbp':rate,'signals':[dict(x) for x in signals],
   'genomes':[dict(x) for x in genomes],'events':[dict(x) for x in events],
   'mind':[dict(x) for x in mind],'experiments':[dict(x) for x in exps],
   'lineage':[dict(x) for x in lineage],'provider_health':health,'research_bloodlines':research,'family_performance':families,'elite_roster':elite,'accelerator':accel,'stake_model':stake_model}
 # IMPORTANT: release the dashboard DB connection before selection telemetry, which
 # acquires its own connection. Otherwise concurrent dashboard requests can exhaust
 # the small asyncpg pool and deadlock each other.
 selection=await selection_snapshot()
 payload['selection']=selection
 payload['reversal_wallet']=await canary_wallet_snapshot()
 payload['capital_shadow']=capital_shadow_snapshot(selection, 0, rate)
 payload['queen_scouts']=await queen_scout_summary()
 payload['biology']=await biology_snapshot()
 payload['drives']=await drives_snapshot()
 payload['swarm_queen']=await swarm_queen_latest()
 payload['platform']=await platform_snapshot(rate)
 return payload


# Stale-while-revalidate cache: the client dashboard should feel instant while
# research aggregation refreshes independently in the background.
_cache_payload=None
_cache_at=0.0
_cache_lock=asyncio.Lock()
_refresh_task=None

async def _refresh_cache():
 global _cache_payload,_cache_at
 async with _cache_lock:
  payload=await _snapshot_fresh()
  _cache_payload=payload; _cache_at=time.time()
  return payload

async def snapshot():
 global _refresh_task
 if _cache_payload is None:
  return await _refresh_cache()
 if time.time()-_cache_at>12 and (_refresh_task is None or _refresh_task.done()):
  _refresh_task=asyncio.create_task(_refresh_cache())
 return _cache_payload

async def warm_loop():
 while True:
  try:
   await _refresh_cache()
  except Exception:
   logging.exception('dashboard_cache_refresh_failed')
  await asyncio.sleep(12)

import json, os, time, urllib.request
from db import connection
from colony.execution_ledger import summary
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
 trades=await conn.fetch('''SELECT intent_id,created_at,mint,side,notional,status,reason,quote,entry_price,mark_price,gross_pnl,friction_cost,net_pnl,broadcast FROM colony_execution_ledger WHERE run_id=$1 ORDER BY id DESC LIMIT 60''',run_id)
 curve=await conn.fetch('''SELECT created_at,net_pnl FROM colony_execution_ledger WHERE run_id=$1 AND net_pnl IS NOT NULL ORDER BY id''',run_id)
 out=[]
 for r in trades:
  d=dict(r);q=d.pop('quote') or {};q=json.loads(q) if isinstance(q,str) else q;d['attribution']=q.get('attribution');out.append(d)
 return {'run_id':run_id,'summary':await summary(run_id),'trades':out,'curve':[dict(x) for x in curve]}
async def snapshot():
 async with connection() as c:
  external=await _run(c,'paper-livequote-v1');native=await _run(c,'colony-native-v1')
  signals=await c.fetch('''SELECT id,created_at,mint,direction,confidence,reference_price FROM signal_events ORDER BY id DESC LIMIT 30''')
  genomes=await c.fetch("""SELECT family,count(DISTINCT genome_id) n FROM colony_forward_entries GROUP BY family ORDER BY family""")
  events=await c.fetch('''SELECT event_type,payload,created_at FROM colony_events ORDER BY id DESC LIMIT 25''')
  mind=await c.fetch("""SELECT run_id,observed_at,status,core,sceptic FROM colony_mind_journal ORDER BY id DESC LIMIT 12""")
  exps=await c.fetch('''SELECT experiment_type,status,created_at FROM colony_mind_experiments ORDER BY id DESC LIMIT 10''')
  lineage=await c.fetch("""SELECT s.id signal_id,f.family,count(DISTINCT f.genome_id) ants FROM signal_events s JOIN colony_forward_entries f ON f.mint=s.mint AND f.observed_at BETWEEN s.created_at-interval '30 minutes' AND s.created_at+interval '5 minutes' WHERE s.id IN (SELECT id FROM signal_events ORDER BY id DESC LIMIT 30) GROUP BY s.id,f.family ORDER BY s.id DESC,ants DESC""")
  fam=await c.fetch('''SELECT quote->'attribution'->>'family' family,count(*) trades,
   count(*) FILTER(WHERE net_pnl>0) wins,coalesce(sum(net_pnl),0) net
   FROM colony_execution_ledger WHERE run_id='colony-native-v1' GROUP BY 1 ORDER BY net DESC''')
  rate=_sol_gbp()
  families=[dict(x) for x in fam]
  for x in families:x['net_gbp']=float(x['net'])*rate if rate is not None else None
  return {'external':external,'native':native,'sol_gbp':rate,'signals':[dict(x) for x in signals],
   'genomes':[dict(x) for x in genomes],'events':[dict(x) for x in events],
   'mind':[dict(x) for x in mind],'experiments':[dict(x) for x in exps],
   'lineage':[dict(x) for x in lineage],'family_performance':families}

"""Forward-only, funded, quote-derived hypothetical accounting. NOT fills or trading.
Never backfill old cash events: admitted evidence must be recorded and timed after activation.
DB advisory lock serializes multiple workers. History rows remain append-only.
"""
import asyncio,json
from db import init_db,connection
from colony.capital_reconciliation import START_LAMPORTS
SCHEMA='''CREATE TABLE IF NOT EXISTS funded_paper_activation(
 id boolean PRIMARY KEY DEFAULT true CHECK(id), started_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE TABLE IF NOT EXISTS funded_paper_event_decisions(
 source_event_id bigint PRIMARY KEY, genome_id text NOT NULL, source_entry_id bigint NOT NULL,
 action text NOT NULL, amount_lamports bigint NOT NULL, accepted boolean NOT NULL,
 reason text NOT NULL, decided_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 evidence text NOT NULL DEFAULT 'hypothetical_quote_not_fill');
CREATE INDEX IF NOT EXISTS funded_paper_event_decisions_genome_idx ON funded_paper_event_decisions(genome_id,source_event_id);'''

def decide(events,initial=START_LAMPORTS):
 """Pure incremental decision function; order is actual journal insertion order."""
 cash={};locked={};seen=set();out=[]
 for r in events:
  gid=str(r['genome_id']);eid=int(r['source_entry_id']);source=int(r['id']);amount=int(r['amount_lamports']);action=r['action'];key=(gid,eid)
  if gid not in cash:cash[gid]=initial
  if amount<=0:ok=False;reason='invalid_amount'
  elif action=='reserve':
   if key in seen:ok=False;reason='duplicate_entry'
   elif cash[gid]<amount:ok=False;reason='insufficient_cash'
   else:ok=True;reason='funded_reservation';cash[gid]-=amount;locked[key]=amount;seen.add(key)
  elif action=='release':
   if key not in locked:ok=False;reason='no_funded_reservation'
   else:ok=True;reason='hypothetical_release';cash[gid]+=amount;del locked[key]
  else:ok=False;reason='invalid_action'
  out.append({'id':source,'genome_id':gid,'source_entry_id':eid,'action':action,'amount_lamports':amount,'accepted':ok,'reason':reason})
 return out,{'cash_lamports':cash,'locked_lamports':{g:sum(v for (owner,_),v in locked.items() if owner==g) for g in cash}}

async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  async with c.transaction():
   await c.execute('SELECT pg_advisory_xact_lock(73581941)')
   await c.execute('INSERT INTO funded_paper_activation(id) VALUES(true) ON CONFLICT DO NOTHING')
   started=await c.fetchval('SELECT started_at FROM funded_paper_activation WHERE id=true')
   rows=await c.fetch('''SELECT id,genome_id,source_entry_id,action,amount_lamports,event_at,recorded_at
    FROM paper_cash_events WHERE recorded_at>= $1 AND event_at >= $1 ORDER BY recorded_at,id''',started)
   events,_=decide(rows)
   for e in events:
    await c.execute('''INSERT INTO funded_paper_event_decisions(source_event_id,genome_id,source_entry_id,action,amount_lamports,accepted,reason)
      VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT(source_event_id) DO NOTHING''',e['id'],e['genome_id'],e['source_entry_id'],e['action'],e['amount_lamports'],e['accepted'],e['reason'])
   decisions=await c.fetch('''SELECT source_event_id id,genome_id,source_entry_id,action,amount_lamports,accepted,reason
    FROM funded_paper_event_decisions ORDER BY source_event_id''')
  return {'activated_at':started.isoformat(),'decision_count':len(decisions),'accepted':sum(bool(x['accepted']) for x in decisions),'rejected':sum(not x['accepted'] for x in decisions),'authority':'hypothetical_funded_events_not_fills_no_live'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

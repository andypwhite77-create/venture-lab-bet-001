"""Research-only attribution of executor-recorded shared fills."""
import asyncio,json,math
from db import init_db,connection
SCHEMA='''CREATE TABLE IF NOT EXISTS ant_wallet_attribution(intent_id bigint NOT NULL,genome_id text NOT NULL,voter_count integer NOT NULL,realized_net_sol double precision NOT NULL,attributed_net_sol double precision NOT NULL,entry_signature text NOT NULL,exit_signature text NOT NULL,evidence_status text NOT NULL DEFAULT 'executor_recorded_not_chain_reconciled',recorded_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(intent_id,genome_id));'''
SQL="""SELECT i.id,i.execution,v.genome_id FROM canary_trade_intents i JOIN canary_intent_votes v ON v.intent_id=i.id WHERE i.broadcast=true AND i.status='closed' ORDER BY i.id,v.genome_id"""
def allocate(rows):
 groups={}
 for row in rows:groups.setdefault(row['id'],[]).append(dict(row))
 out=[];skipped=[]
 for iid,group in groups.items():
  e=group[0]['execution'] or {}
  if isinstance(e,str):e=json.loads(e)
  try:
   net=float(e['realized_market_pnl_after_network_fees_sol']);entry=e['entry_signature'];exit=e['exit_signature']
   if not math.isfinite(net) or not entry or not exit:raise ValueError('invalid')
  except (KeyError,ValueError,TypeError):skipped.append(iid);continue
  voters=sorted({row['genome_id'] for row in group})
  for voter in voters:out.append((iid,voter,len(voters),net,net/len(voters),entry,exit))
 return out,skipped
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  entries,skipped=allocate(await c.fetch(SQL))
  if entries:await c.executemany('''INSERT INTO ant_wallet_attribution(intent_id,genome_id,voter_count,realized_net_sol,attributed_net_sol,entry_signature,exit_signature) VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING''',entries)
  rows=await c.fetch('SELECT genome_id,count(*) n,sum(attributed_net_sol) pnl_sol FROM ant_wallet_attribution GROUP BY genome_id ORDER BY pnl_sol DESC')
 return {'entries':len(entries),'excluded_intents':skipped,'ants':[dict(row) for row in rows],'authority':'research_only','warning':'Shared votes are not causal P/L; executor records require independent on-chain verification.'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

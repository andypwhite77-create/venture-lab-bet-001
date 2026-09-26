"""Create attributed colony-native paper intents from prospective ant entries."""
import json,time
from db import connection
from colony.trade_executor import Limits,execute_simulated
from colony.execution_ledger import record
from colony.execution_safety import state
from colony.jupiter_quotes import quote,SOL
LAMPORTS=1_000_000_000
async def groups(limit=20):
 async with connection() as c:
  rows=await c.fetch('''SELECT e.candidate_id,e.mint,e.family,array_agg(DISTINCT e.genome_id) genomes,
   count(DISTINCT e.genome_id) ants,min(e.observed_at) observed_at,c.entry_price
   FROM colony_forward_entries e JOIN research_candidates c ON c.id=e.candidate_id
   GROUP BY e.candidate_id,e.mint,e.family,c.entry_price ORDER BY e.candidate_id DESC LIMIT $1''',limit)
 return [dict(r) for r in rows]
async def process_group(g,run_id='colony-native-v1',notional_sol=.005):
 iid=f"native-{g['candidate_id']}-{g['family']}-v1";st=await state(run_id)
 intent={'intent_id':iid,'mint':g['mint'],'side':'buy','notional':notional_sol,'max_slippage_bps':100,'created_at':time.time()}
 attribution={'candidate_id':g['candidate_id'],'family':g['family'],'genomes':g['genomes'],'ants':g['ants'],'reference_price':g['entry_price']}
 try:q=quote(SOL,g['mint'],int(notional_sol*LAMPORTS),100);q['attribution']=attribution;q['signal_reference_price']=g['entry_price']
 except Exception as e:q={'attribution':attribution,'error':type(e).__name__};r={'accepted':False,'reason':'quote_failed','broadcast':False,'mode':'simulated'};await record(intent,r,q,run_id);return r
 r=execute_simulated(intent,Limits(max_notional=.01,max_open_notional=.1),st,q);await record(intent,r,q,run_id);return r
async def run_once(limit=20):
 out=[]
 for g in await groups(limit):out.append({'candidate_id':g['candidate_id'],'family':g['family'],'ants':g['ants'],'result':await process_group(g)})
 return out
if __name__=='__main__':
 import asyncio
 from db import init_db
 async def main():await init_db();print(json.dumps(await run_once(),default=str))
 asyncio.run(main())

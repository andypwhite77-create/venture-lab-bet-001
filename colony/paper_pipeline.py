"""Signal -> live quote -> hard risk gate -> persistent simulated execution."""
import time
from db import connection
from colony.trade_executor import Limits,execute_simulated
from colony.execution_ledger import record
from colony.execution_safety import state
from colony.jupiter_quotes import quote,SOL
LAMPORTS=1_000_000_000
async def candidates(limit=20):
 async with connection() as c:
  rows=await c.fetch('''SELECT id,mint,direction,confidence,reference_price,created_at FROM signal_events
   WHERE direction='long_candidate' AND reference_price IS NOT NULL ORDER BY id DESC LIMIT $1''',limit)
 return [dict(r) for r in rows]
async def process_signal(row,run_id='paper-livequote-v1',notional_sol=.02):
 iid=f"signal-{row['id']}-jup-v1"; s=await state(run_id)
 intent={'intent_id':iid,'mint':row['mint'],'side':'buy','notional':notional_sol,
  'max_slippage_bps':100,'created_at':time.time()}
 try:q=quote(SOL,row['mint'],int(notional_sol*LAMPORTS),100)
 except Exception as e:
  result={'accepted':False,'reason':'quote_failed','broadcast':False,'mode':'simulated'}
  await record(intent,result,{'error':type(e).__name__},run_id);return result
 result=execute_simulated(intent,Limits(max_notional=.05,max_open_notional=.5),s,q)
 q['signal_reference_price']=row.get('reference_price'); await record(intent,result,q,run_id);return result
async def run_once(limit=5):
 rows=await candidates(limit);out=[]
 for r in rows:
  out.append({'signal_id':r['id'],'mint':r['mint'],'result':await process_signal(r)})
 return out
if __name__=='__main__':
 import asyncio,json
 from db import init_db
 async def main():
  await init_db();print(json.dumps(await run_once(),default=str))
 asyncio.run(main())

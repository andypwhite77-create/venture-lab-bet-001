"""Create attributed colony-native paper intents from prospective ant entries."""
import json,time,os
from db import connection
from colony.trade_executor import Limits,execute_simulated
from colony.execution_ledger import record
from colony.execution_safety import state
from colony.jupiter_quotes import quote,SOL
from colony.paper_economics import TARGET_STAKE_GBP,notional_sol
LAMPORTS=1_000_000_000
async def groups(limit=20):
 cutoff=int(os.getenv('PAPER_V2_START_AFTER_CANDIDATE_ID','0'))
 async with connection() as c:
  rows=await c.fetch("""WITH elite_entries AS (
    SELECT e.candidate_id,e.mint,'reversal'::text family,e.genome_id,e.observed_at,e.hold_minutes
      FROM reversal_tournament_entries e WHERE e.candidate_id > $2
    UNION ALL
    SELECT e.candidate_id,e.mint,r.family,e.genome_id,e.observed_at,e.hold_minutes
      FROM family_tournament_entries e JOIN family_tournament_runs r ON r.run_id=e.run_id
      WHERE e.candidate_id > $2
   )
   SELECT e.candidate_id,e.mint,e.family,array_agg(DISTINCT e.genome_id) genomes,
      count(DISTINCT e.genome_id) ants,min(e.observed_at) observed_at,min(e.hold_minutes) hold_minutes,max(e.hold_minutes) max_hold_minutes,c.entry_price
   FROM elite_entries e JOIN research_candidates c ON c.id=e.candidate_id
   GROUP BY e.candidate_id,e.mint,e.family,c.entry_price ORDER BY e.candidate_id DESC LIMIT $1""",limit,cutoff)
 return [dict(r) for r in rows]
async def process_group(g,run_id='colony-native-v2-25gbp',notional=None):
 if notional is None:
  notional,rate,rate_source=notional_sol(TARGET_STAKE_GBP)
 else:
  rate,rate_source=None,'explicit_notional'
 iid=f"native-{g['candidate_id']}-{g['family']}-v2-25gbp";st=await state(run_id)
 intent={'intent_id':iid,'mint':g['mint'],'side':'buy','notional':notional,'max_slippage_bps':100,'created_at':time.time()}
 attribution={'candidate_id':g['candidate_id'],'family':g['family'],'genomes':g['genomes'],'ants':g['ants'],'reference_price':g['entry_price'],
              'target_stake_gbp':TARGET_STAKE_GBP,'sol_gbp_rate':rate,'rate_source':rate_source,'hold_minutes':g['hold_minutes'],'max_hold_minutes':g['max_hold_minutes']}
 try:q=quote(SOL,g['mint'],int(notional*LAMPORTS),100);q['attribution']=attribution;q['signal_reference_price']=g['entry_price']
 except Exception as e:q={'attribution':attribution,'error':type(e).__name__};r={'accepted':False,'reason':'quote_failed','broadcast':False,'mode':'simulated'};await record(intent,r,q,run_id);return r
 r=execute_simulated(intent,Limits(max_notional=1.0,max_open_notional=5.0),st,q);await record(intent,r,q,run_id);return r
async def run_once(limit=20):
 out=[]
 for g in await groups(limit):out.append({'candidate_id':g['candidate_id'],'family':g['family'],'ants':g['ants'],'result':await process_group(g)})
 return out
if __name__=='__main__':
 import asyncio
 from db import init_db
 async def main():await init_db();print(json.dumps(await run_once(),default=str))
 asyncio.run(main())

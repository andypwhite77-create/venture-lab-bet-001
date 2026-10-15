"""Read-only daily paper comparison. No live or promotion authority."""
import asyncio,json
from collections import defaultdict
from db import init_db,connection
SQL="""SELECT d.action,l.outcome_at,l.paper_pnl_gbp FROM plasticity_forward_decisions d JOIN controlled_paper_trade_ledger l ON l.entry_id=d.entry_id ORDER BY l.outcome_at,l.entry_id"""
def summarize(rows):
 days=defaultdict(lambda:{'fixed_dna':0.,'plasticity':0.,'fixed_dna_trades':0,'plasticity_trades':0})
 for r in rows:
  x=days[r['outcome_at'].date().isoformat()];profit=float(r['paper_pnl_gbp']);x['fixed_dna']+=profit;x['fixed_dna_trades']+=1
  if r['action']=='follow_dna':x['plasticity']+=profit;x['plasticity_trades']+=1
 result={}
 for variant in ('fixed_dna','plasticity'):
  active=[x for x in days.values() if x[variant+'_trades']>0]
  result[variant]={'active_days':len(active),'profitable_days':sum(x[variant]>0 for x in active),'losing_days':sum(x[variant]<0 for x in active),'total_nominal_paper_gbp':round(sum(x[variant] for x in days.values()),3),'worst_day_gbp':round(min((x[variant] for x in active),default=0),3)}
 return {'variants':result,'days':[{'day':d,**v} for d,v in sorted(days.items())],'authority':'shadow_only_no_live','limitation':'Matched hypothetical outcome marks; not executed fills or same-period original live Canary comparison'}
async def run():
 await init_db()
 async with connection() as c:rows=await c.fetch(SQL)
 return summarize(rows)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

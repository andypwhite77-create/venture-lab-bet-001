"""Indicative SOL round-trip economics from truly paired forward quotes only."""
import asyncio,json,statistics
from db import init_db,connection

def evaluate(pairs,fee_sol=0.00001):
 out=[]
 for r in pairs:
  a=r['entry_quote'];b=r['exit_quote']
  if isinstance(a,str):a=json.loads(a)
  if isinstance(b,str):b=json.loads(b)
  try:
   sent=int(a['in_amount']);tokens=int(a['out_amount']);returned=int(b['out_amount'])
   if sent<=0 or tokens<=0 or int(b['in_amount'])!=tokens:continue
   # Quotes use exact input/output amounts. Fee is conservative hypothetical
   # two-transaction cost; no realised fills/MEV/priority tips implied.
   net=(returned-sent)/1e9-fee_sol
   pnl_pct=100*net/(sent/1e9)
   out.append({'entry_id':r['entry_id'],'net_sol':round(net,9),'net_pct':round(pnl_pct,4),
    'entry_latency_seconds':r['entry_latency'],'exit_latency_seconds':r['exit_latency']})
  except (ValueError,TypeError,KeyError):continue
 return out
async def run():
 await init_db()
 async with connection() as c:
  rows=await c.fetch("""SELECT a.entry_id,a.quote entry_quote,b.quote exit_quote,
      a.latency_seconds entry_latency,b.latency_seconds exit_latency
      FROM canary_forward_quote_observations a
      JOIN canary_forward_quote_observations b ON b.entry_id=a.entry_id AND b.phase='exit'
      WHERE a.phase='entry' AND a.status='quoted' AND b.status='quoted'
      AND a.latency_seconds BETWEEN 0 AND 120 AND b.latency_seconds BETWEEN 0 AND 120""")
 out=evaluate([dict(x) for x in rows]);values=[x['net_pct'] for x in out]
 return {'paired_quote_count':len(out),'mean_indicative_net_pct':round(statistics.fmean(values),4) if values else None,
  'worst_indicative_net_pct':min(values) if values else None,
  'negative_quoted_pairs':sum(v<0 for v in values),
  'authority':'indicative_only_no_fills_or_live','fees':'hypothetical 0.00001 SOL per round trip; other costs and impact may be higher'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

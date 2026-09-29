"""Conservative £25 Reversal canary wallet from prospective matured evidence.
Research-only: no signing/broadcasting. One wallet, no imaginary concurrent capital.
"""
from db import connection
START_GBP=25.0
async def snapshot():
 async with connection() as c:
  rows=await c.fetch("""WITH x AS (
   SELECT e.mint,e.observed_at,e.hold_minutes,o.net_return_pct,
    row_number() over(partition by e.mint order by e.observed_at) rn
   FROM reversal_tournament_entries e
   JOIN reversal_tournament_ants a ON a.run_id=e.run_id AND a.genome_id=e.genome_id AND a.baseline=true AND a.active=true
   JOIN LATERAL (SELECT net_return_pct,horizon_minutes FROM research_outcomes o WHERE o.candidate_id=e.candidate_id
    ORDER BY abs(o.horizon_minutes-e.hold_minutes),o.horizon_minutes LIMIT 1) o ON true)
   SELECT mint,observed_at,hold_minutes,net_return_pct FROM x WHERE rn=1 ORDER BY observed_at""")
 bal=START_GBP; peak=bal; worst_dd=0.0; wins=0; curve=[]
 for r in rows:
  before=bal; ret=float(r['net_return_pct']); bal*=max(0.0,1+ret/100.0); wins+=int(ret>0)
  peak=max(peak,bal); worst_dd=min(worst_dd,(bal/peak-1)*100.0)
  curve.append({'mint':r['mint'],'observed_at':r['observed_at'],'hold_minutes':r['hold_minutes'],'return_pct':ret,'before_gbp':before,'after_gbp':bal})
 return {'start_gbp':START_GBP,'balance_gbp':bal,'profit_gbp':bal-START_GBP,'return_pct':(bal/START_GBP-1)*100,
  'trades':len(rows),'wins':wins,'win_rate_pct':(wins/len(rows)*100 if rows else None),'worst_drawdown_pct':worst_dd,
  'basis':'baseline reversal; unique prospective mints; nearest measured hold horizon; modelled research costs','live_fill_verified':False,'curve':curve}

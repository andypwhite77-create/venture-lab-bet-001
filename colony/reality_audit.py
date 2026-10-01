"""Canonical Reversal reality audit: sequential £25, unique prospective mints.
Uses recorded prospective outcomes and separately reports executable-quote coverage.
"""
from db import connection
START_GBP=25.0

async def reversal():
    async with connection() as c:
        rows=await c.fetch('''WITH x AS (
          SELECT e.mint,e.observed_at,e.hold_minutes,o.net_return_pct,e.candidate_id,
           row_number() over(partition by e.mint order by e.observed_at,e.id) rn
          FROM reversal_tournament_entries e
          JOIN reversal_tournament_ants a ON a.run_id=e.run_id AND a.genome_id=e.genome_id
          JOIN LATERAL (SELECT net_return_pct FROM research_outcomes o WHERE o.candidate_id=e.candidate_id AND o.horizon_minutes=e.hold_minutes LIMIT 1) o ON true
          WHERE a.baseline=true AND a.active=true)
          SELECT * FROM x WHERE rn=1 ORDER BY observed_at''')
        reality=await c.fetchrow('''SELECT count(*) accepted,
          count(*) FILTER(WHERE execution_reality IS NOT NULL) reality_rows,
          count(*) FILTER(WHERE execution_reality->>'ok'='true') executable_rows
          FROM colony_execution_ledger WHERE status='accepted' ''')
    bal=START_GBP; peak=bal; worst=0.0; wins=0; curve=[]
    for r in rows:
        before=bal; ret=float(r['net_return_pct']); bal=max(0.0,bal*(1+ret/100)); wins+=ret>0
        peak=max(peak,bal); worst=min(worst,100*(bal/peak-1))
        curve.append({'mint':r['mint'],'observed_at':r['observed_at'],'before_gbp':before,'return_pct':ret,'after_gbp':bal})
    return {'start_gbp':START_GBP,'end_gbp':bal,'net_gbp':bal-START_GBP,'trades':len(rows),'wins':wins,
      'win_rate_pct':100*wins/len(rows) if rows else None,'worst_drawdown_pct':worst,
      'capital_model':'single sequential wallet; unique mint first observation; no concurrent reuse',
      'execution_reality_coverage':dict(reality) if reality else {},'curve':curve}

"""Deterministic Reversal live-canary evidence gate. No authority to enable trading."""
import os
from db import connection
CURRENT_CODE_START_ID=int(os.getenv('REVERSAL_CURRENT_CODE_START_ID','0'))
MIN_OPPS=int(os.getenv('REVERSAL_CANARY_MIN_OPPS','30'))
MIN_EXEC_COVERAGE=float(os.getenv('REVERSAL_CANARY_MIN_EXEC_COVERAGE','0.90'))
MAX_DRAWDOWN=float(os.getenv('REVERSAL_CANARY_MAX_DRAWDOWN_PCT','30'))

async def status():
 async with connection() as c:
  rows=await c.fetch('''WITH x AS (SELECT e.candidate_id,e.mint,e.observed_at,e.hold_minutes,o.net_return_pct,
    row_number() over(partition by e.mint order by e.observed_at,e.id) rn
    FROM reversal_tournament_entries e JOIN reversal_tournament_ants a ON a.run_id=e.run_id AND a.genome_id=e.genome_id
    JOIN LATERAL(SELECT net_return_pct FROM research_outcomes o WHERE o.candidate_id=e.candidate_id AND o.horizon_minutes=e.hold_minutes LIMIT 1)o ON true
    WHERE a.baseline=true AND a.active=true AND e.candidate_id>$1) SELECT * FROM x WHERE rn=1 ORDER BY observed_at''',CURRENT_CODE_START_ID)
  er=await c.fetchrow("SELECT count(*) total,count(*) FILTER(WHERE execution_reality->>'ok'='true') executable FROM colony_execution_ledger WHERE run_id='colony-native-v3-holdaware' AND coalesce((quote->'attribution'->>'candidate_id')::bigint,0)>$1",CURRENT_CODE_START_ID)
  faults=await c.fetchval("SELECT coalesce((SELECT (auditor->>'fault_count')::int FROM colony_audit_snapshots ORDER BY id DESC LIMIT 1),0)")
  controls=await c.fetch("SELECT control,count(*) FILTER(WHERE included) n,avg(return_pct) FILTER(WHERE included) avg_return FROM reversal_paired_controls WHERE candidate_id>$1 GROUP BY control",CURRENT_CODE_START_ID)
 bal=25.;peak=bal;worst=0.;wins=0
 for r in rows:
  ret=float(r['net_return_pct']);bal=max(0.,bal*(1+ret/100));wins+=ret>0;peak=max(peak,bal);worst=min(worst,100*(bal/peak-1))
 coverage=(int(er['executable'])/int(er['total'])) if er and er['total'] else 0.
 control_stats={x['control']:{'n':x['n'],'avg_return_pct':float(x['avg_return']) if x['avg_return'] is not None else None} for x in controls}
 reversal_avg=(sum(float(r['net_return_pct']) for r in rows)/len(rows)) if rows else None
 control_edge=bool(rows) and all(v['n']>=5 and v['avg_return_pct'] is not None and reversal_avg>v['avg_return_pct'] for v in control_stats.values()) and len(control_stats)>=2
 checks={'control_edge':control_edge,'independent_opportunities':len(rows)>=MIN_OPPS,'positive_net':bal>25.,'drawdown_ok':abs(worst)<=MAX_DRAWDOWN,
         'execution_coverage':coverage>=MIN_EXEC_COVERAGE,'auditor_clean':faults==0}
 return {'eligible_evidence':all(checks.values()),'authority_granted':False,'checks':checks,'opportunities':len(rows),'end_gbp':bal,
         'net_gbp':bal-25.,'wins':wins,'worst_drawdown_pct':worst,'execution_coverage':coverage,'audit_faults':faults,
         'thresholds':{'min_opportunities':MIN_OPPS,'min_execution_coverage':MIN_EXEC_COVERAGE,'max_drawdown_pct':MAX_DRAWDOWN},
         'reversal_avg_return_pct':reversal_avg,'controls':control_stats,'note':'Evidence eligibility is not live authority; human approval remains required.'}

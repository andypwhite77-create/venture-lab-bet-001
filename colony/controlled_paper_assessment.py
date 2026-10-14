"""Conservative, observation-only family research triage.

These paper outcome marks are neither executable fills nor independent samples.
No outcome can authorize genome changes, breeding, promotion or live trading.
"""
MIN_COMPLETED = 30
MIN_DISTINCT_MINTS = 10
MAX_WORST_LOSS_PCT = -20.0

async def snapshot(conn):
    try:
        rows = await conn.fetch("""SELECT family, count(*)::int completed,
          count(DISTINCT mint)::int distinct_mints,
          round(avg(net_return_pct)::numeric,3) mean_net_pct,
          round(min(net_return_pct)::numeric,3) worst_net_pct,
          round(sum(paper_pnl_gbp)::numeric,3) nominal_paper_pnl_gbp,
          count(*) FILTER (WHERE net_return_pct < -20)::int tail_over_20pct,
          count(*) FILTER (WHERE net_return_pct > 0)::int winning_marks
          FROM controlled_paper_trade_ledger
          GROUP BY family ORDER BY family""")
        result=[]
        for r in rows:
            n=int(r['completed']); distinct=int(r['distinct_mints']); mean=float(r['mean_net_pct']); worst=float(r['worst_net_pct']); tail=int(r['tail_over_20pct'])
            blockers=[]
            if n < MIN_COMPLETED: blockers.append('insufficient_completed_marks')
            if distinct < MIN_DISTINCT_MINTS: blockers.append('insufficient_distinct_mints')
            if mean <= 0: blockers.append('nonpositive_mean_after_assumed_costs')
            if worst < MAX_WORST_LOSS_PCT or tail: blockers.append('material_loss_tail')
            if not blockers: blockers.append('independent_forward_execution_validation_missing')
            if 'material_loss_tail' in blockers: action='investigate_tail_and_exit_mechanics'
            elif mean <= 0: action='diagnose_negative_expectancy'
            elif n < MIN_COMPLETED or distinct < MIN_DISTINCT_MINTS: action='collect_more_independent_forward_marks'
            else: action='design_paired_forward_execution_simulation'
            result.append({'family':r['family'],'completed':n,'distinct_mints':distinct,
               'mean_net_pct':mean,'worst_net_pct':worst,'tail_over_20pct':tail,
               'winning_marks':int(r['winning_marks']),'nominal_paper_pnl_gbp':float(r['nominal_paper_pnl_gbp']),
               'research_action':action,'blockers':blockers,'candidate_status':'research_only_not_qualified'})
        return {'status':'ok','methodology':'descriptive_marks_only_no_independence_or_execution_claim',
          'minimum_completed_marks':MIN_COMPLETED,'minimum_distinct_mints':MIN_DISTINCT_MINTS,
          'authority':'advisory_only_no_breeding_no_spartan_no_live', 'families':result}
    except Exception as exc:
        return {'status':'unavailable','error_type':type(exc).__name__,
          'authority':'advisory_only_no_breeding_no_spartan_no_live'}

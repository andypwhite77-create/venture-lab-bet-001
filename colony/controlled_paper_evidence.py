"""Read-only, forward-only experimental paper cohort evidence for Swarm Queen."""
async def snapshot(conn):
 try:
  rows=await conn.fetch("""SELECT c.family,
   count(l.entry_id)::int completed,
   count(l.entry_id) FILTER (WHERE l.net_return_pct>0)::int wins,
   round(avg(l.net_return_pct)::numeric,3) mean_net_pct,
   round(min(l.net_return_pct)::numeric,3) worst_net_pct,
   round(sum(l.paper_pnl_gbp)::numeric,3) net_paper_gbp,
   count(l.entry_id) FILTER (WHERE l.net_return_pct < -20)::int severe_losses,
   count(l.entry_id) FILTER (WHERE l.net_return_pct > 30)::int extreme_winners,
   count(e.id)::int entries
   FROM controlled_paper_cohort c
   LEFT JOIN eve_reference_paper_entries e
     ON e.genome_id=c.genome_id AND e.observed_at>=c.started_at
   LEFT JOIN controlled_paper_trade_ledger l ON l.entry_id=e.id
   WHERE c.status='observation_only'
   GROUP BY c.family ORDER BY c.family""")
  return {'status':'ok','authority':'advisory_only_no_breeding_no_spartan_no_live',
    'interpretation':'Research-outcome marks, not executable fills; overlapping entries and missing marks may bias P/L. Never use for promotion.',
    'families':[{'family':r['family'],'entries':r['entries'],'completed':r['completed'],
      'pending':r['entries']-r['completed'],'wins':r['wins'],
      'mean_net_pct':float(r['mean_net_pct']) if r['mean_net_pct'] is not None else None,
      'worst_net_pct':float(r['worst_net_pct']) if r['worst_net_pct'] is not None else None,
      'paper_pnl_gbp':float(r['net_paper_gbp']) if r['net_paper_gbp'] is not None else None,
      'severe_losses':r['severe_losses'],'extreme_winners':r['extreme_winners'],
      'research_priority':'audit_outlier_prices_and_execution' if r['extreme_winners'] else ('reduce_loss_tails' if r['severe_losses'] else 'collect_more_forward_evidence')} for r in rows]}
 except Exception as exc:
  return {'status':'unavailable','error_type':type(exc).__name__,
    'authority':'advisory_only_no_breeding_no_spartan_no_live'}

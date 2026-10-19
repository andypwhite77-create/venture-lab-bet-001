"""Conservative pre-paper screening; never treat training fitness as proof of earnings."""
def assess(row):
 if not row.get('spartan_passed'):return False,'spartan_not_passed'
 notes=row.get('notes') or {}
 if not isinstance(notes,dict):return False,'missing_auditable_evidence'
 folds=notes.get('walk_forward')
 if not isinstance(folds,list) or len(folds)<3:return False,'insufficient_independent_walk_forward_folds'
 for f in folds:
  if not isinstance(f,dict):return False,'malformed_fold'
  # Mixed historical reports sometimes omit crucial economic fields: reject.
  try:
   n=int(f['n']);mean=float(f['avg_net_return_pct']);median=float(f['median_net_return_pct']);worst=float(f['worst_net_return_pct'])
  except (ValueError,TypeError,KeyError):return False,'missing_after_cost_tail_evidence'
  if n<25 or mean<=2 or median<=0 or worst < -15:return False,'weak_or_tail_heavy_walk_forward'
 return True,'passed_conservative_pre_paper_screen_only'

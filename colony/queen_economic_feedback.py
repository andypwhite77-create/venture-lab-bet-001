"""Read-only family diagnostic feedback; no model reward or trading authority."""
def explain(attribution):
 output={}
 for family,books in attribution.get('families',{}).items():
  completed=sum(b['completed_quote_round_trips'] for b in books)
  pending=sum(b['pending_positions'] for b in books)
  net=sum(b['realized_hypothetical_net_sol'] for b in books)
  locked=sum(b['locked_sol'] for b in books)
  drawdown=max((b['realized_drawdown_sol'] for b in books),default=0)
  tags=[]
  if net<0:tags.append('investigate_negative_quote_economics')
  if pending:tags.append('investigate_unresolved_capital')
  if drawdown>max(net,0):tags.append('investigate_loss_tail')
  if completed<25:tags.append('insufficient_completed_round_trips')
  output[family]={'completed':completed,'pending':pending,'hypothetical_net_sol':round(net,9),'locked_sol':round(locked,9),'max_genome_drawdown_sol':drawdown,'research_priorities':tags,'budget_bonus':0,'economic_reward':None,'promotion_allowed':False}
 return {'families':output,'unmapped_count':attribution.get('unmapped_count',0),'authority':'diagnostic_only_no_budget_increase','warning':'Symptoms are not proven causes. Paper quotes are not fills.'}

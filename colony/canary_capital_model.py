"""Bounded sequential £25 paper bankroll scenario. No optimistic refill, no leverage."""
def replay(returns,initial_gbp=25,stake_gbp=25,extra_cost_pct=1):
 cash=float(initial_gbp);peak=cash;worst=0;trades=0;skipped=0
 for ret in returns:
  stake=min(float(stake_gbp),cash)
  if stake<=0:skipped+=1;continue
  # Loss cannot debit more than deployed cash; transaction cost is borne by cash.
  pnl=stake*(float(ret)-extra_cost_pct)/100
  cash=max(0,cash+pnl);peak=max(peak,cash)
  worst=min(worst,100*(cash/peak-1));trades+=1
 return {'initial_gbp':initial_gbp,'end_gbp':round(cash,4),'trades':trades,'skipped_insufficient_capital':skipped,
         'max_drawdown_pct':round(worst,3),'extra_cost_pct':extra_cost_pct,
         'limitations':'Sequential hypothetical marks, not concurrent positions or fills; not valid for promotion.'}

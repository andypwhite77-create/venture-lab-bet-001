"""Fail-closed execution-evidence gate for any Solana genome advancement.
Spartan results remain archival; no quote validation can enable live trading.
"""
def verdict(genome_id,books,min_pairs=25):
 book=(books or {}).get(str(genome_id))
 if not book:return {'eligible':False,'reason':'no_matching_prospective_quote_cohort'}
 if book.get('capital_reconciled') is not True:return {'eligible':False,'reason':'capital_ledger_not_verified'}
 if int(book.get('cash_event_rejections') or 0)>0:return {'eligible':False,'reason':'cash_event_reconciliation_failed'}
 if int(book.get('quote_pairs') or 0)<min_pairs:return {'eligible':False,'reason':'insufficient_quote_pairs'}
 if int(book.get('missing_or_invalid_pairs') or 0)>0:return {'eligible':False,'reason':'unresolved_or_invalid_quotes'}
 if int(book.get('blocked_by_simulated_cash') or 0)>0:return {'eligible':False,'reason':'capital_constraint'}
 if float(book.get('unresolved_reserved_sol') or 0)>0:return {'eligible':False,'reason':'capital_unresolved'}
 if float(book.get('stressed_net_sol') or 0)<=0:return {'eligible':False,'reason':'no_positive_stressed_profit'}
 return {'eligible':True,'reason':'research_quote_gate_only_not_live_approval'}

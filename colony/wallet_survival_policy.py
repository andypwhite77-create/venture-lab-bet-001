"""Pure, auditable live-roster decision advisory; no wallet writes or live authority."""
from dataclasses import dataclass
@dataclass(frozen=True)
class WalletEvidence:
    closed_trades:int
    net_realized_gbp:float
    unrealized_inventory_gbp:float
    wallet_reconciled:bool
    unresolved_exits:int
    risk_breach:bool=False

def classify(e:WalletEvidence,minimum_trades=25):
    if e.risk_breach:return {'stage':'suspend_for_review','reason':'risk_limit_breach','authority':'advisory_only'}
    if not e.wallet_reconciled:return {'stage':'suspend_for_review','reason':'unreconciled_wallet','authority':'advisory_only'}
    if e.unresolved_exits:return {'stage':'suspend_for_review','reason':'unresolved_live_exit','authority':'advisory_only'}
    if e.closed_trades<minimum_trades:return {'stage':'probation','reason':'insufficient_closed_trades','authority':'advisory_only'}
    if e.net_realized_gbp<=0:return {'stage':'demote_to_research','reason':'nonpositive_realized_wallet_surplus','authority':'advisory_only'}
    return {'stage':'eligible_for_retention_review','reason':'positive_reconciled_realized_wallet_surplus','authority':'advisory_only'}

import unittest
from datetime import datetime,timedelta,timezone
from colony.shared_wallet_shadow import simulate
T=datetime(2026,10,16,tzinfo=timezone.utc)
def row(i,candidate,minute,return_pct=10,action='follow_dna'):
 at=T+timedelta(minutes=minute)
 return dict(entry_id=i,genome_id=str(i),candidate_id=candidate,entry_at=at,stake_gbp=25,action=action,
 outcome_at=at+timedelta(minutes=5) if return_pct is not None else None,
 captured_at=at+timedelta(minutes=5) if return_pct is not None else None,net_return_pct=return_pct)
class WalletTests(unittest.TestCase):
 def test_duplicate_same_market_blocked(self):
  x=simulate([row(1,4,0),row(2,4,1)],start_gbp=50,as_of=T+timedelta(minutes=15))['results']['fixed_dna'];self.assertEqual(x['counts']['duplicate_candidate_blocked'],1)
 def test_limited_cash(self):
  x=simulate([row(1,1,0,None),row(2,2,1,None)],start_gbp=25,as_of=T+timedelta(minutes=100))['results']['fixed_dna'];self.assertEqual(x['counts']['no_cash'],1);self.assertEqual(x['unresolved']['overdue'],1)
 def test_abstain_preserves_cash(self):
  x=simulate([row(1,1,0,-50,'abstain')],start_gbp=25,as_of=T+timedelta(minutes=15))['results']['plasticity'];self.assertEqual(x['cash_gbp'],25)
 def test_accounting_equation(self):
  x=simulate([row(1,1,0,25)],start_gbp=25,as_of=T+timedelta(minutes=15))['results']['fixed_dna'];self.assertEqual(x['accounting_delta_gbp'],0)
if __name__=='__main__':unittest.main()

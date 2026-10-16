import unittest
from datetime import datetime,timedelta,timezone
from colony.shared_wallet_recovery_audit import review
T=datetime(2026,10,16,tzinfo=timezone.utc)
class RecoveryTests(unittest.TestCase):
 def test_missing_quote_stays_locked(self):
  r=dict(entry_id=1,genome_id='g',candidate_id=1,entry_at=T,stake_gbp=25,action='follow_dna',outcome_at=None,captured_at=None,net_return_pct=None,entry_status='quoted',exit_status=None,entry_latency=.1,exit_latency=None)
  x=review([r],as_of=T+timedelta(hours=2))['unresolved_review']['fixed_dna']
  self.assertEqual(x['reasons']['exit_quote_missing'],1)
  self.assertEqual(x['haircut_scenarios_gbp']['0'],0)
  self.assertEqual(x['locked_gbp'],25)

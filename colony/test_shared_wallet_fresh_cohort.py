import unittest
from datetime import datetime,timezone,timedelta
from colony.shared_wallet_shadow import simulate
class CohortTests(unittest.TestCase):
 def test_empty_new_cohort_has_full_cash(self):
  x=simulate([],as_of=datetime(2026,10,16,tzinfo=timezone.utc))
  for policy in x['results'].values():
   self.assertEqual(policy['cash_gbp'],125)
   self.assertEqual(policy['locked_gbp'],0)
   self.assertEqual(policy['accounting_delta_gbp'],0)

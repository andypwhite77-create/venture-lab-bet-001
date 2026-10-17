import unittest
from colony.wallet_survival_review import assess
class ReviewTests(unittest.TestCase):
 def test_vote_is_not_profit(self):
  x=assess([{'genome_id':'a','canary_slot':1,'observed_intents':30,'broadcast_intents':30,'attributed_ledger_rows':30}])
  self.assertEqual(x['ants'][0]['decision']['stage'],'suspend_for_review')
  self.assertFalse(x['ants'][0]['automatic_roster_change'])

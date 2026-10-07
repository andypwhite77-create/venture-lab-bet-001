import inspect,unittest
from colony import canary_controller as cc

class CanaryRosterControllerTests(unittest.TestCase):
 def test_signal_source_is_fixed_champion_canary_roster(self):
  src=inspect.getsource(cc.latest_canary_groups)
  self.assertIn('champion_paper_entries',src)
  self.assertIn('canary_slot IS NOT NULL',src)
  self.assertIn("interval '3 minutes'",src)
  self.assertNotIn('reversal_tournament_entries',src)

 def test_voters_are_persisted_for_future_individual_canary_evidence(self):
  src=inspect.getsource(cc.record_intent)
  self.assertIn('canary_intent_votes',src)
  self.assertIn("v['genome_id']",src)

if __name__=='__main__':unittest.main()

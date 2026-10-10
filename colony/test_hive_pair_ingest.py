import unittest
from colony.hive_pair_ingest import SQL,FRICTION_PCT
class PairIngestTests(unittest.TestCase):
 def test_targeted_tag_and_control_required(self):
  self.assertIn("c.species='loss_tail_challenger'",SQL)
  self.assertIn('b.baseline=true',SQL)
  self.assertIn('b.candidate_id=c.candidate_id',SQL)
 def test_prospective_cutoff_and_friction(self):
  self.assertIn('c.observed_at>$1',SQL)
  self.assertIn('b.observed_at>$1',SQL)
  self.assertGreaterEqual(FRICTION_PCT,0)

import unittest
from colony.queen_opportunity_queue import validate_submission,KINDS
class ProposalTests(unittest.TestCase):
 def test_major_short_is_researchable(self):
  self.assertIn('major_asset_short',KINDS)
  validate_submission('major_asset_short','Major asset repricing','Hypothesis from public order-book data with defined invalidation.','swarm_queen',{'public_data':'quoted' },['liquidity gap'])
 def test_evidence_required(self):
  with self.assertRaises(ValueError):validate_submission('major_asset_short','Major asset repricing','Hypothesis from public order-book data with defined invalidation.','swarm_queen',{},['liquidity gap'])
 def test_failure_modes_required(self):
  with self.assertRaises(ValueError):validate_submission('major_asset_short','Major asset repricing','Hypothesis from public order-book data with defined invalidation.','swarm_queen',{'public_data':'quoted'},[])

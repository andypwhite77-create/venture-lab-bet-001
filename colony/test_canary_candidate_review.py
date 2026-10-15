import unittest
from colony.canary_candidate_review import assess
class CanaryReviewTests(unittest.TestCase):
 def row(self,**changes):
  r=dict(source='champion_paper',genome_id='test',distinct_mints=30,completed=30,pending=0,mean_mark_pct=2,capped_mean_pct=2,median_mark_pct=1,worst_mark_pct=-5,severe_losses=0,wins=20,suspect_marks=0,fee_exceeds_stake_marks=0,newest_signal=None)
  r.update(changes);return r
 def test_clean_paper_is_never_promoted(self):
  x=assess(self.row());self.assertEqual(x['tier'],'research_shortlist');self.assertIn('no_independent_executable_forward_validation',x['blockers'])
 def test_extreme_invalid_return_is_veto(self):
  x=assess(self.row(suspect_marks=1));self.assertEqual(x['tier'],'research_repair')
 def test_negative_median_blocks_outlier_driven_average(self):
  x=assess(self.row(mean_mark_pct=40,median_mark_pct=-2));self.assertEqual(x['tier'],'research_repair')

class TailVetoTests(unittest.TestCase):
 def test_outlier_adjusted_negative_return_blocks(self):
  row=dict(source='champion_paper',genome_id='test',distinct_mints=30,completed=30,pending=0,mean_mark_pct=30,capped_mean_pct=-3,median_mark_pct=1,worst_mark_pct=-5,severe_losses=0,wins=20,suspect_marks=0,fee_exceeds_stake_marks=0,newest_signal=None)
  self.assertIn('capped_return_not_economically_positive',assess(row)['blockers'])

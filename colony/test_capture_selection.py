import unittest
from colony.queen_pattern_recognition import selection_fitness

class CaptureSelection(unittest.TestCase):
 def metrics(self, **kw):
  d={'n':100,'avg_net_gbp':1.5,'median_return_pct':2.0,'worst_return_pct':-12.0,'outlier':0.1,'win_rate':.62,'nursery_score':.3,'low_age_fraction':0,'low_liquidity_fraction':0}
  d.update(kw);return d
 def test_negative_median_rejected(self):
  self.assertEqual(selection_fitness([self.metrics(),self.metrics(median_return_pct=-1)]),-999.0)
 def test_severe_tail_rejected(self):
  self.assertEqual(selection_fitness([self.metrics(),self.metrics(worst_return_pct=-30)]),-999.0)
 def test_negative_economics_rejected(self):
  self.assertEqual(selection_fitness([self.metrics(avg_net_gbp=-1),self.metrics()]),-999.0)
 def test_faster_capital_capture_rewards_short_hold(self):
  parts=[self.metrics(),self.metrics()]
  self.assertGreater(selection_fitness(parts,{'parameters':{'hold_minutes':5}}),selection_fitness(parts,{'parameters':{'hold_minutes':60}}))

if __name__=='__main__':unittest.main()

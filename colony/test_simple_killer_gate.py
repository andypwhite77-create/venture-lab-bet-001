import unittest
from colony.simple_killer_gate import assess

class SimpleKillerGateTests(unittest.TestCase):
 def test_good_but_few_observations_rejected(self):
  self.assertFalse(assess([8]*24,[0]*24,24)['passes_screen'])
 def test_stress_erases_edge(self):
  self.assertFalse(assess([1]*30,[0]*30,30)['passes_screen'])
 def test_benchmark_must_be_beaten(self):
  self.assertFalse(assess([4]*30,[6]*30,30)['passes_screen'])
 def test_extreme_losses_rejected(self):
  self.assertFalse(assess([-40]*3+[12]*27,[0]*30,30)['passes_screen'])
 def test_good_repeatable_simple_candidate(self):
  self.assertTrue(assess([4]*30,[0]*30,30)['passes_screen'])
 def test_distinctness_required(self):
  self.assertFalse(assess([4]*50,[0]*50,3)['passes_screen'])
 def test_non_finite_rejected(self):
  self.assertFalse(assess([float('nan')]*30,[0]*30,30)['passes_screen'])

if __name__=='__main__':unittest.main()

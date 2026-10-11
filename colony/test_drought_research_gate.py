import unittest
from colony.queen_survival_loop import drought_research_gate
class DroughtGateTests(unittest.TestCase):
 def test_ten_failures_pause(self):self.assertTrue(drought_research_gate({'spartan_drought_campaigns':10})['paused'])
 def test_nine_does_not(self):self.assertFalse(drought_research_gate({'spartan_drought_campaigns':9})['paused'])
 def test_explicit_override(self):self.assertFalse(drought_research_gate({'spartan_drought_campaigns':10},True)['paused'])

import unittest
from pathlib import Path
class SamplerFullCoverageHealthTests(unittest.TestCase):
 def test_health_requires_full_coverage_for_active_cohort(self):
  src=Path('/app/path_sampler.py').read_text()
  self.assertIn('result["recorded"] == result["active"]',src)
  self.assertNotIn('result["recorded"] > 0',src)

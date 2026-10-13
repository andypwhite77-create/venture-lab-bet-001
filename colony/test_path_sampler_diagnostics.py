import unittest
from pathlib import Path
class SamplerDiagnosticsTests(unittest.TestCase):
 def test_health_exposes_sampling_yield(self):
  s=Path('/app/path_sampler.py').read_text()
  self.assertIn('"coverage_ratio": round(recorded/len(rows),4)',s)
  self.assertIn('result["active"] == 0 or result["recorded"] == result["active"]',s)
  a=Path('/app/app.py').read_text()
  self.assertIn('"last_path_result": state.get("last_path_result")',a)

import unittest
from pathlib import Path
class PairedCullTests(unittest.TestCase):
 def test_explicit_freeze_guard(self):
  code=Path('/app/colony/family_tournament.py').read_text()
  self.assertIn("cfg.get('mode')=='forward_shadow_paired_frozen'",code)
  self.assertIn("'status':'protected_paired_cohort'",code)

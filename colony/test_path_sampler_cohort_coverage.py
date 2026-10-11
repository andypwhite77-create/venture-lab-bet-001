import unittest
from pathlib import Path
class PathSamplerCohortCoverageTest(unittest.TestCase):
 def test_experiment_candidates_included_without_opening_all_research_candidates(self):
  source=Path('/app/research_db.py').read_text()
  definition=source.split('async def active_shadow_candidates(',1)[1].split('async def record_price_path(',1)[0]
  self.assertIn('shadow_trade=TRUE OR EXISTS',definition)
  self.assertIn("fr.config->>'mode'='forward_shadow_paired_frozen'",definition)
  self.assertIn("fr.status='collecting'",definition)
  self.assertIn("entry_price IS NOT NULL",definition)
  self.assertIn("created_at >= NOW()",definition)

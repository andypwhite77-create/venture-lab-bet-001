import unittest
from pathlib import Path
class MarketDataServiceTests(unittest.TestCase):
 def test_only_separate_collector_owns_sampling(self):
  app=Path('/app/app.py').read_text()
  self.assertNotIn('asyncio.create_task(path_sampler_loop(state))',app)
  self.assertIn('"market_data_fresh": market_fresh',app)
  service=Path('/app/market_data_service.py').read_text()
  self.assertIn('await sample_active_paths()',service)
  self.assertIn('await archive_recent()',service)
 def test_data_history_has_provenance(self):
  schema=Path('/app/research_db.py').read_text()
  self.assertIn('CREATE TABLE IF NOT EXISTS market_price_history',schema)
  self.assertIn('source_path_id BIGINT UNIQUE',schema)

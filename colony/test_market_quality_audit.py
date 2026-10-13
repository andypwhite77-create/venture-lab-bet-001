import unittest
from datetime import datetime,timedelta,timezone
from colony.market_quality_audit import coverage,classify,disagreement
class QualityAuditTests(unittest.TestCase):
 def test_incomplete_path_cannot_pass(self):
  t=datetime(2026,10,13,tzinfo=timezone.utc)
  self.assertFalse(coverage([t,t+timedelta(minutes=30)],t,t+timedelta(minutes=30))['complete'])
 def test_regular_path_passes(self):
  t=datetime(2026,10,13,tzinfo=timezone.utc)
  self.assertTrue(coverage([t+timedelta(minutes=i) for i in range(31)],t,t+timedelta(minutes=30))['complete'])
 def test_insufficient_history_has_no_regime(self):
  self.assertEqual(classify([1,2]),'insufficient')
 def test_crosscheck_requires_different_providers(self):
  t=datetime(2026,10,13,tzinfo=timezone.utc)
  one=[{'provider':'a','price':10,'collected_at':t},{'provider':'a','price':11,'collected_at':t}]
  self.assertEqual(disagreement(one)['pairs'],0)
  one.append({'provider':'b','price':12,'collected_at':t})
  self.assertGreater(disagreement(one)['pairs'],0)

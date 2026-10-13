import unittest
from datetime import datetime,timedelta,timezone
from colony.market_reliability_report import summarize
class ReliabilityReportTests(unittest.TestCase):
 def test_does_not_pass_short_window(self):
  now=datetime.now(timezone.utc)
  rows=[{'completed_at':now-timedelta(minutes=i),'active':2,'recorded':2,'details':{'required_mints':['A'],'missing_mints':[]}} for i in range(20)]
  result=summarize(rows,now=now)
  self.assertFalse(result['coverage_target_met']);self.assertFalse(result['window_complete'])
  self.assertTrue(result['tokens'][0]['reliable_95pct'])
 def test_token_failure_and_missing_legacy_inventory(self):
  now=datetime.now(timezone.utc)
  rows=[{'completed_at':now,'active':2,'recorded':1,'details':{'required_mints':['A','B'],'missing_mints':['B'],'provider_failures':{'B':['birdeye:HTTP_429']}}}, {'completed_at':now-timedelta(minutes=1),'active':2,'recorded':1,'details':{}}]
  result=summarize(rows,now=now)
  self.assertEqual(result['weighted_coverage'],.5)
  self.assertEqual(result['token_scoring_cycles'],1)
  self.assertEqual(result['tokens'][1]['reasons']['birdeye:HTTP_429'],1)

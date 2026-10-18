import unittest
from datetime import datetime,timedelta,timezone
from colony.entry_failure_lab import evaluate
T=datetime(2026,10,18,tzinfo=timezone.utc)
def make(i,liquidity,ret,complete=True):
 return {'candidate_id':i,'entry_at':T+timedelta(minutes=i),'features':{'liquidity_usd':liquidity},'outcome':{'stop_10_take_15':{'status':'observed_path' if complete else 'insufficient_path','net_pct':ret}}}
class EntryFailureTests(unittest.TestCase):
 def test_chronological_holdout_and_missing_data(self):
  rows=[make(i,100+i,i-12) for i in range(10)]+[make(11,None,0,False)]
  r=evaluate(rows)
  self.assertEqual((r['training_n'],r['holdout_n'],r['excluded']),(7,3,1))
  self.assertEqual(r['features']['liquidity_usd']['status'],'insufficient_training_feature_coverage')
 def test_training_threshold_only(self):
  rows=[make(i,100+i,-2) for i in range(10)]+[make(i,100000+i,5) for i in range(10,14)]
  r=evaluate(rows);f=r['features']['liquidity_usd']
  self.assertEqual(r['training_n'],9)
  self.assertEqual(f['train_median_threshold'],104)
  self.assertEqual(f['chronological_holdout']['high_n'],5)
 def test_no_fabricated_returns(self):
  r=evaluate([make(1,100,5,False)])
  self.assertEqual(r['matched_outcomes'],0)

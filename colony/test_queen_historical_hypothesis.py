import unittest
from datetime import datetime,timedelta,timezone
from colony.queen_historical_hypothesis import test
T=datetime(2026,1,1,tzinfo=timezone.utc)
def rows():
 return [{'candidate_id':i,'created_at':T+timedelta(days=i),'mint':f'm{i}','features':{'liquidity_usd':i*100},'net_return_pct':i-4} for i in range(10)]
class Tests(unittest.TestCase):
 def test_mint_holdout(self):
  r=test(rows(),'liquidity_usd','high')
  self.assertEqual(r['training_mints'],7)
  self.assertEqual(r['holdout_mints'],3)
  self.assertEqual(r['training_median'],300)
 def test_reject_unapproved_feature(self):
  with self.assertRaises(ValueError):test(rows(),'admin_password','high')
 def test_insufficient_independent_assets(self):
  self.assertEqual(test(rows()[:4],'liquidity_usd','low')['status'],'insufficient_independent_mints')

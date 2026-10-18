import unittest
from datetime import datetime,timedelta,timezone
from colony.queen_pair_hypothesis import evaluate
T=datetime(2026,1,1,tzinfo=timezone.utc)
def rows():
 return [{'candidate_id':i,'created_at':T+timedelta(days=i),'mint':f'm{i}','features':{'liquidity_usd':i*100,'volume_m5':i*10},'net_return_pct':i-10} for i in range(40)]
class Tests(unittest.TestCase):
 def test_chronological_partition(self):
  x=evaluate(rows(),'liquidity_usd','high','volume_m5','high')
  self.assertEqual((x['training_mints'],x['later_mints']),(28,12))
  self.assertEqual(x['training_thresholds'],[1350,135])
 def test_reject_same_feature(self):
  with self.assertRaises(ValueError):evaluate(rows(),'liquidity_usd','high','liquidity_usd','low')
 def test_mint_floor(self):
  self.assertEqual(evaluate(rows()[:10],'liquidity_usd','high','volume_m5','high')['status'],'insufficient_independent_mints')

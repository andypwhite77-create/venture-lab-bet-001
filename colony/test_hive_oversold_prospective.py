import unittest
from colony.hive_oversold_prospective import evaluate
class SelectionTests(unittest.TestCase):
 def test_unobserved_does_not_count(self):
  rows=[{'selected':True,'status':'observed_path','net_pct':2.0},{'selected':False,'status':'observed_path','net_pct':1.0},{'selected':False,'status':'insufficient_path'}]
  r=evaluate(rows,1)
  self.assertEqual(r['edge'],1.0)
  self.assertEqual(r['excluded'],1)
 def test_small_sample_no_proof(self):
  self.assertEqual(evaluate([{'selected':True,'status':'observed_path','net_pct':5.0}])['status'],'insufficient_evidence')

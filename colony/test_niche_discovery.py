import unittest
from colony.niche_discovery import discover
class DiscoveryTests(unittest.TestCase):
 def test_thin_data_proposes_nothing(self): self.assertEqual(discover([{'x':1,'return_pct':20}]),[])
 def test_detects_joint_regime(self):
  rows=[]
  for i in range(30): rows.append({'a':1 if i<15 else -1,'b':1 if i<15 else -1,'return_pct':12 if i<15 else 0})
  p=discover(rows,min_n=10,min_effect=5); self.assertTrue(any(x['features']==['a__high','b__high'] for x in p))
 def test_small_effect_ignored(self):
  rows=[{'a':1,'b':1,'return_pct':1} for _ in range(15)]+[{'a':-1,'b':-1,'return_pct':0} for _ in range(15)]
  self.assertEqual(discover(rows,min_n=10,min_effect=5),[])
if __name__=='__main__':unittest.main()

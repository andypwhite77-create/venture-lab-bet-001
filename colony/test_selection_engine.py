import unittest
from colony.selection_engine import shadow_plan
class SelectionTests(unittest.TestCase):
 def ants(self): return [
  {'id':'elite','family':'a','rank_fraction':.02,'evidence_n':30},
  {'id':'mid','family':'b','rank_fraction':.5,'evidence_n':30},
  {'id':'bad','family':'b','rank_fraction':.99,'evidence_n':30},
  {'id':'rarebad','family':'rare','rank_fraction':.99,'evidence_n':30}]
 def test_shadow_only(self): self.assertEqual(shadow_plan(self.ants(),{'a':.2,'b':.78,'rare':.02})['mode'],'shadow_only')
 def test_elite_breeds(self): self.assertIn('elite',shadow_plan(self.ants(),{'a':.2,'b':.78,'rare':.02})['breeders'])
 def test_bad_replaceable(self): self.assertIn('bad',shadow_plan(self.ants(),{'a':.2,'b':.78,'rare':.02})['replace'])
 def test_rare_family_not_culled(self): self.assertNotIn('rarebad',shadow_plan(self.ants(),{'a':.2,'b':.78,'rare':.02})['replace'])
if __name__=='__main__':unittest.main()

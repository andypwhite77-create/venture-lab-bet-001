import unittest
from colony.niches import classify,niche_fitness,specialist_bonus
class NicheTests(unittest.TestCase):
 def test_multi_niche(self):
  x=classify({'age_minutes':5,'liquidity_usd':10000,'momentum_pct':20}); self.assertIn('new_launch',x); self.assertIn('thin_liquidity',x); self.assertIn('high_momentum',x)
 def test_generalist_fallback(self): self.assertEqual(classify({}),['generalist'])
 def test_specialist_needs_evidence(self): self.assertEqual(specialist_bonus(.8,.1,3),0)
 def test_specialist_can_beat_global_rank(self): self.assertGreater(specialist_bonus(.8,.1,20),0)
 def test_niche_scores(self): self.assertEqual(niche_fitness([{'niches':['risk_off'],'return_pct':2},{'niches':['risk_off'],'return_pct':4}])['risk_off']['mean_return_pct'],3)
if __name__=='__main__':unittest.main()

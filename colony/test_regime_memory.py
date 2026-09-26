import unittest
from colony.regime_memory import summarize,drift,stale_weight
class RegimeTests(unittest.TestCase):
 def test_summary_needs_evidence(self): self.assertEqual(summarize([{'niches':['x'],'return_pct':2}],5),{})
 def test_drift_detected(self):
  a={'x':{'mean':10}}; b={'x':{'mean':2}}; self.assertEqual(drift(a,b)[0]['direction'],'degraded')
 def test_small_drift_ignored(self): self.assertEqual(drift({'x':{'mean':1}},{'x':{'mean':2}}),[])
 def test_old_evidence_decays(self):
  self.assertEqual(stale_weight(0),1); self.assertEqual(stale_weight(4),.5); self.assertLess(stale_weight(12),.2)
if __name__=='__main__':unittest.main()

import unittest,time
from colony.trade_executor import Limits,validate,execute_simulated
class T(unittest.TestCase):
 def i(self,**x):
  d={'intent_id':'x1','mint':'M','side':'buy','notional':5,'max_slippage_bps':100,'created_at':time.time()};d.update(x);return d
 def test_ok(self):self.assertTrue(validate(self.i(),Limits(),{})[0])
 def test_notional(self):self.assertEqual(validate(self.i(notional=11),Limits(),{})[1],'notional_limit')
 def test_stale(self):self.assertEqual(validate(self.i(created_at=time.time()-20),Limits(),{})[1],'stale_intent')
 def test_loss_kill(self):self.assertEqual(validate(self.i(),Limits(),{'daily_pnl':-50})[1],'daily_loss_kill')
 def test_duplicate(self):self.assertEqual(validate(self.i(),Limits(),{'seen_ids':{'x1'}})[1],'duplicate')
 def test_no_broadcast(self):self.assertFalse(execute_simulated(self.i(),Limits(),{}, {'slippage_bps':20})['broadcast'])
if __name__=='__main__':unittest.main()

import unittest
from colony.mind_contract import validate,envelope
class MindTests(unittest.TestCase):
 def test_core_can_hypothesise(self): self.assertTrue(validate(envelope('core','hypothesis','x'),'core')[0])
 def test_core_cannot_trade(self): self.assertFalse(validate({'action':'execute_trade','reasoning_summary':'x'},'core')[0])
 def test_core_cannot_change_threshold(self): self.assertFalse(validate({'action':'change_threshold','reasoning_summary':'x'},'core')[0])
 def test_sceptic_cannot_approve_population(self): self.assertFalse(validate({'action':'change_population','reasoning_summary':'x'},'sceptic')[0])
 def test_sceptic_can_veto(self): self.assertTrue(validate(envelope('sceptic','veto','thin evidence'),'sceptic')[0])
if __name__=='__main__':unittest.main()

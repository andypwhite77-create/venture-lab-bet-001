import unittest
from colony.funded_paper_ledger import decide
def e(id,entry,action,amount,g='a'):
 return {'id':id,'source_entry_id':entry,'action':action,'amount_lamports':amount,'genome_id':g}
class FundedTests(unittest.TestCase):
 def test_insufficient_cash_cannot_release(self):
  decisions,state=decide([e(1,1,'reserve',110),e(2,1,'release',120)],100)
  self.assertEqual([x['accepted'] for x in decisions],[False,False])
  self.assertEqual(state['cash_lamports']['a'],100)
 def test_funded_ledger_recycles_cash(self):
  events=[e(1,1,'reserve',80),e(2,2,'reserve',30),e(3,1,'release',84),e(4,3,'reserve',90)]
  decisions,state=decide(events,100)
  self.assertEqual([x['accepted'] for x in decisions],[True,False,True,True])
  self.assertEqual(state['cash_lamports']['a'],14)
 def test_duplicate_rejected(self):
  d,_=decide([e(1,1,'reserve',30),e(2,1,'reserve',30)],100)
  self.assertEqual([x['accepted'] for x in d],[True,False])
 def test_distinct_genomes_independent(self):
  d,s=decide([e(1,1,'reserve',80),e(2,2,'reserve',80,'b')],100)
  self.assertTrue(all(x['accepted'] for x in d))
  self.assertEqual(s['cash_lamports'],{'a':20,'b':20})

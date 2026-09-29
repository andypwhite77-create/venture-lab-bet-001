import unittest
from colony.independent_auditor import recompute

class AuditInvariantTests(unittest.TestCase):
    def row(self,**kw):
        x={'side':'buy','notional':1.0,'entry_price':10.0,'mark_price':11.0,'friction_cost':.01}
        x.update(kw); return x
    def test_buy_recompute(self):
        x=recompute(self.row()); self.assertAlmostEqual(x['gross'],.1); self.assertAlmostEqual(x['net'],.09)
    def test_sell_direction(self):
        x=recompute(self.row(side='sell',mark_price=9.0)); self.assertAlmostEqual(x['gross'],.1)
    def test_friction_subtracted(self):
        x=recompute(self.row(friction_cost=.05)); self.assertAlmostEqual(x['net'],.05)
    def test_invalid_entry_fails(self):
        self.assertEqual(recompute(self.row(entry_price=0))['fault'],'invalid_numeric')
    def test_unmarked_is_not_invented(self):
        self.assertIsNone(recompute(self.row(mark_price=None)))

if __name__=='__main__': unittest.main()

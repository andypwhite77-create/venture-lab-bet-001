import unittest
from colony.resource_ecology import allocation

class ResourceEcologyTests(unittest.TestCase):
    def test_one_lucky_trade_cannot_reproduce(self):
        a=allocation(.01,1)
        self.assertFalse(a['can_reproduce'])
        self.assertLess(a['paper_notional'],50)
    def test_proven_elite_gets_resources(self):
        a=allocation(.01,30)
        self.assertTrue(a['can_reproduce'])
        self.assertGreater(a['paper_notional'],25)
    def test_proven_bottom_loses_resources(self):
        self.assertLess(allocation(.99,30)['paper_notional'],25)
    def test_bounds_hold(self):
        for r in (0,.5,1):
            a=allocation(r,100,1)
            self.assertGreaterEqual(a['paper_notional'],10)
            self.assertLessEqual(a['paper_notional'],50)

if __name__=='__main__': unittest.main()

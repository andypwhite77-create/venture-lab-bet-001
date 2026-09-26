import unittest
from colony.ecology import pressures

class EcologyTests(unittest.TestCase):
    def test_thin_evidence_mutes_selection(self):
        a=pressures(.05,1); b=pressures(.05,30)
        self.assertLess(a['reproductive_access'],b['reproductive_access'])
    def test_elite_gets_more_reproductive_access(self):
        self.assertGreater(pressures(.05,30)['reproductive_access'],pressures(.50,30)['reproductive_access'])
    def test_bottom_gets_replacement_pressure(self):
        self.assertGreater(pressures(.98,30)['replacement_pressure'],pressures(.50,30)['replacement_pressure'])
    def test_catastrophe_can_force_pressure(self):
        self.assertGreater(pressures(.5,30,.2)['replacement_pressure'],0)

if __name__=='__main__': unittest.main()

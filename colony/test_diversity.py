import unittest
from colony.diversity import diversity_multiplier,adjusted_reproductive_access,protected_family

class DiversityTests(unittest.TestCase):
    def test_normal_share_unpenalized(self):
        self.assertEqual(diversity_multiplier(.20),1)
    def test_dominance_penalized(self):
        self.assertLess(diversity_multiplier(.40),diversity_multiplier(.30))
    def test_monoculture_nearly_sterile(self):
        self.assertEqual(adjusted_reproductive_access(1,.60),.1)
    def test_rare_family_protected(self):
        self.assertTrue(protected_family(.02)); self.assertFalse(protected_family(.05))

if __name__=='__main__': unittest.main()

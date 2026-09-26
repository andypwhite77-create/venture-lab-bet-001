import unittest
from colony.execution_reconcile import friction
class T(unittest.TestCase):
 def test_zero(self):self.assertEqual(friction(10),0)
 def test_bps(self):self.assertAlmostEqual(friction(100,50),.5)
 def test_network(self):self.assertAlmostEqual(friction(5,100,.01),.06)
if __name__=='__main__':unittest.main()

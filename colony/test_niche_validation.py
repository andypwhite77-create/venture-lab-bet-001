import unittest
from colony.niche_validation import Validation
class ValidationTests(unittest.TestCase):
 def test_old_data_rejected(self):
  v=Validation(('a',),100,5); self.assertFalse(v.observe(100,{'a':True},10)); self.assertEqual(v.future_yes,[])
 def test_future_pattern_validates(self):
  v=Validation(('a',),100,5)
  for i in range(10): v.observe(101+i,{'a':True},8)
  for i in range(10): v.observe(201+i,{'a':False},0)
  self.assertTrue(v.result()['validated'])
 def test_reversal_fails(self):
  v=Validation(('a',),100,5)
  for i in range(10): v.observe(101+i,{'a':True},-8)
  for i in range(10): v.observe(201+i,{'a':False},0)
  self.assertFalse(v.result()['validated'])
 def test_needs_both_sides(self):
  v=Validation(('a',),100,5)
  for i in range(20): v.observe(101+i,{'a':True},8)
  self.assertEqual(v.result()['reason'],'insufficient_future_data')
if __name__=='__main__':unittest.main()

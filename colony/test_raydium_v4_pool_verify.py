import unittest
from colony.raydium_v4_pool_verify import decode,PROGRAM
class Tests(unittest.TestCase):
 def test_reject_other_program(self):
  with self.assertRaises(ValueError):decode(bytes(752),'different')
 def test_reject_wrong_length(self):
  with self.assertRaises(ValueError):decode(bytes(750),PROGRAM)
 def test_reject_invalid_status(self):
  with self.assertRaises(ValueError):decode(bytes(752),PROGRAM)

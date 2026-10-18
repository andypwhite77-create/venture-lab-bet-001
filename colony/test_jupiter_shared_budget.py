import unittest
from unittest.mock import patch
from colony import jupiter_shared_budget
class Tests(unittest.TestCase):
 def test_fails_closed_without_connection(self):
  with patch.object(jupiter_shared_budget,'DSN',''):
   self.assertFalse(jupiter_shared_budget.acquire())
 def test_fails_closed_on_database_error(self):
  with patch.object(jupiter_shared_budget,'DSN','postgresql://invalid'):
   with patch.object(jupiter_shared_budget.asyncio,'run',side_effect=RuntimeError):
    self.assertFalse(jupiter_shared_budget.acquire())

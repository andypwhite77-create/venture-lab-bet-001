import unittest
from unittest.mock import patch
from colony.canary_rent_auto import account_still_empty, MIN_LAMPORTS, ACTIVE

class RentAutoSafetyTests(unittest.TestCase):
    def test_finalized_zero_only(self):
        a={'token_account':'a','mint':'mint','program':'program','lamports':1513840}
        ok={'value':{'owner':'program','lamports':1513840,'data':{'parsed':{'info':{'mint':'mint','tokenAmount':{'amount':'0'}}}}}}
        with patch('colony.canary_rent_auto.rpc_call',return_value=ok):
            self.assertTrue(account_still_empty(a))
        for value in (None, {'owner':'program','lamports':1513840,'data':{'parsed':{'info':{'mint':'mint','tokenAmount':{'amount':'1'}}}}}, {'owner':'wrong','lamports':1513840,'data':{'parsed':{'info':{'mint':'mint','tokenAmount':{'amount':'0'}}}}}):
            with patch('colony.canary_rent_auto.rpc_call',return_value={'value':value}):
                self.assertFalse(account_still_empty(a))
    def test_reserve_guard(self):
        self.assertGreaterEqual(MIN_LAMPORTS,1000000)
        for state in ('open','recovery','uncertain','submitting_entry','submitting_exit','claimed'):
            self.assertIn(state,ACTIVE)

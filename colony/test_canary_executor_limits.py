import unittest
from unittest.mock import patch
from colony import canary_executor as ce

BASE={
    'active_ants':36,'votes':36,'vote_fraction':1.0,'hold_minutes':5,
    'mint':'TokenMint','requested_sol':0.011235955056179775,'requested_gbp':1.0,
}

class CanaryLimitTests(unittest.TestCase):
    @patch.object(ce,'wallet_address',return_value=ce.EXPECTED)
    def test_fx_rise_shrinks_amount_to_one_pound(self,_):
        amount=ce.limits(dict(BASE),100.0,0.0674)
        self.assertLessEqual(amount*100.0,1.00000001)
        self.assertAlmostEqual(amount,0.01,places=12)

    @patch.object(ce,'wallet_address',return_value=ce.EXPECTED)
    def test_fx_fall_never_grows_above_original_sol_intent(self,_):
        amount=ce.limits(dict(BASE),80.0,0.0674)
        self.assertAlmostEqual(amount,BASE['requested_sol'],places=12)

    @patch.object(ce,'wallet_address',return_value=ce.EXPECTED)
    def test_requested_gbp_over_cap_is_rejected(self,_):
        row=dict(BASE,requested_gbp=1.01)
        with self.assertRaisesRegex(ValueError,'trade_cap'):
            ce.limits(row,90.0,0.0674)

    def test_gateway_slippage_http_error_is_prebroadcast(self):
        body=b'{"statusCode":400,"code":"SLIPPAGE_EXCEEDED","message":"price moved"}'
        self.assertEqual(ce.classify_gateway_http_error(400,body),'SLIPPAGE_EXCEEDED')

    def test_gateway_timeout_is_not_classified_prebroadcast(self):
        body=b'{"statusCode":504,"code":"TRANSACTION_TIMEOUT","message":"unknown"}'
        self.assertIsNone(ce.classify_gateway_http_error(504,body))

    def test_landed_failure_is_not_classified_prebroadcast(self):
        body=b'{"statusCode":400,"code":"TRANSACTION_FAILED","message":"landed"}'
        self.assertIsNone(ce.classify_gateway_http_error(400,body))

if __name__=='__main__': unittest.main()

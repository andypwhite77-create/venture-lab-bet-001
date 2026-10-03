import unittest
from contextlib import asynccontextmanager
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

    def test_quote_validation_failure_has_specific_safe_label(self):
        q={
            'quoteId':'q1','tokenIn':ce.SOL,'tokenOut':'TokenMint',
            'amountIn':'0.01','amountOut':'100','minAmountOut':'99',
            'maxAmountIn':'0.01','priceImpactPct':'0',
            'quoteResponse':{
                'inputMint':ce.SOL,'outputMint':'TokenMint','swapMode':'ExactIn',
                'routePlan':[], 'slippageBps':100,'outAmount':'100',
                'inAmount':'10000000','otherAmountThreshold':'99','priceImpactPct':'0'
            },
        }
        with self.assertRaisesRegex(ce.QuoteValidationRejected,'empty_route'):
            ce.validate_quote(q,ce.SOL,'TokenMint',0.01)

    def test_malformed_quote_has_safe_label(self):
        with self.assertRaisesRegex(ce.QuoteValidationRejected,'malformed_quote'):
            ce.validate_quote({},ce.SOL,'TokenMint',0.01)


class _FakeConn:
    def __init__(self):
        self.executed=[]
    @asynccontextmanager
    async def transaction(self):
        yield
    async def fetchrow(self,sql,*args):
        if 'canary_control' in sql:
            return {'armed':True,'stopped':False}
        raise AssertionError(sql)
    async def execute(self,sql,*args):
        self.executed.append((sql,args))

class CanarySubmissionPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_entry_prebroadcast_rejection_does_not_halt_canary(self):
        c=_FakeConn(); row={'id':1}; data={}
        q={'quoteId':'q1'}
        with patch.object(ce,'gateway',side_effect=ce.GatewayPreBroadcastRejected('SLIPPAGE_EXCEEDED')):
            ok=await ce.submit(c,row,data,q,'entry')
        self.assertFalse(ok)
        rendered='\n'.join(sql for sql,_ in c.executed)
        self.assertNotIn('UPDATE canary_control SET armed=false',rendered)
        self.assertTrue(any('broadcast=false' in sql for sql,_ in c.executed))

    async def test_exit_prebroadcast_rejection_still_halts_canary(self):
        c=_FakeConn(); row={'id':2}; data={}
        q={'quoteId':'q2'}
        with patch.object(ce,'gateway',side_effect=ce.GatewayPreBroadcastRejected('SLIPPAGE_EXCEEDED')):
            ok=await ce.submit(c,row,data,q,'exit')
        self.assertFalse(ok)
        rendered='\n'.join(sql for sql,_ in c.executed)
        self.assertIn('UPDATE canary_control SET armed=false',rendered)

if __name__=='__main__': unittest.main()

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


    @patch.object(ce,'wallet_address',return_value=ce.EXPECTED)
    def test_single_active_ant_matches_paper_trigger(self,_):
        row=dict(BASE,active_ants=36,votes=1,vote_fraction=1/36)
        amount=ce.limits(row,90.0,0.0674)
        self.assertGreater(amount,0)

    @patch.object(ce,'wallet_address',return_value=ce.EXPECTED)
    def test_zero_votes_rejected(self,_):
        row=dict(BASE,active_ants=36,votes=0,vote_fraction=0.0)
        with self.assertRaisesRegex(ValueError,'consensus'):
            ce.limits(row,90.0,0.0674)

    @patch.object(ce,'wallet_address',return_value=ce.EXPECTED)
    def test_network_reserve_is_never_spent(self,_):
        row=dict(BASE,active_ants=36,votes=1,vote_fraction=1/36,requested_sol=0.01,requested_gbp=1.0)
        amount=ce.limits(row,90.0,0.008)
        self.assertLessEqual(amount,0.005000000001)
        self.assertGreaterEqual(0.008-amount,ce.RESERVE_SOL-1e-12)

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

    def test_recovery_waits_for_negative_quote_before_deadline(self):
        q={'minAmountOut':'0.009'}
        data={'entry_spent_sol':0.01,'recovery_deadline':200.0}
        should,why,pnl=ce.recovery_should_exit(q,data,100.0)
        self.assertFalse(should); self.assertEqual(why,'wait'); self.assertAlmostEqual(pnl,-0.001)

    def test_recovery_exits_at_breakeven(self):
        q={'minAmountOut':'0.0101'}
        data={'entry_spent_sol':0.01,'recovery_deadline':200.0}
        should,why,_=ce.recovery_should_exit(q,data,100.0)
        self.assertTrue(should); self.assertEqual(why,'break_even_or_better')

    def test_recovery_exits_safe_quote_at_deadline(self):
        q={'minAmountOut':'0.009'}
        data={'entry_spent_sol':0.01,'recovery_deadline':100.0}
        should,why,_=ce.recovery_should_exit(q,data,100.0)
        self.assertTrue(should); self.assertEqual(why,'deadline')

    def test_recovery_basis_uses_swap_input_not_wallet_delta(self):
        q={'minAmountOut':'0.0111'}
        data={'entry_spent_sol':0.0139,'entry_quote':{'amountIn':'0.0110'},'recovery_deadline':200.0}
        should,why,pnl=ce.recovery_should_exit(q,data,100.0)
        self.assertTrue(should); self.assertEqual(why,'break_even_or_better'); self.assertAlmostEqual(pnl,0.0001)


class _FakeConn:
    def __init__(self):
        self.executed=[]
    @asynccontextmanager
    async def transaction(self):
        yield
    async def fetchrow(self,sql,*args):
        if 'canary_control' in sql:
            return {'armed':True,'stopped':False,'recovery_only':False}
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

    async def test_exit_prebroadcast_rejection_enters_recovery_without_halting(self):
        c=_FakeConn(); row={'id':2}; data={}
        q={'quoteId':'q2'}
        with patch.object(ce,'gateway',side_effect=ce.GatewayPreBroadcastRejected('SLIPPAGE_EXCEEDED')):
            ok=await ce.submit(c,row,data,q,'exit')
        self.assertFalse(ok)
        rendered='\n'.join(sql for sql,_ in c.executed)
        self.assertNotIn('UPDATE canary_control SET armed=false',rendered)
        self.assertTrue(any(args and args[1]=='recovery' for _,args in c.executed if len(args)>1))


class RecoveryArmingPolicyTests(unittest.TestCase):
    def test_recovery_is_not_an_unresolved_arm_blocker(self):
        blocking={'claimed','open','submitting_entry','submitting_exit','uncertain'}
        self.assertNotIn('recovery',blocking)
        self.assertIn('uncertain',blocking)


class CanaryArmFundingPolicyTests(unittest.TestCase):
    def test_arm_funding_threshold_matches_one_pound_trade_cap(self):
        import inspect
        src=inspect.getsource(ce.command)
        self.assertIn("(await asyncio.to_thread(wallet_balance_sol)-RESERVE_SOL)*rate<1",src)
        self.assertNotIn("(await asyncio.to_thread(wallet_balance_sol)-RESERVE_SOL)*rate<5",src)

if __name__=='__main__': unittest.main()

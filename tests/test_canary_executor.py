import unittest
from unittest.mock import patch
from colony.canary_executor import validate_quote, limits, EXPECTED, SOL

class SafetyTests(unittest.TestCase):
    def quote(self):
        return dict(quoteId='q',tokenIn=SOL,tokenOut='token',amountIn=.01,amountOut=100,minAmountOut=99,maxAmountIn=.01,priceImpactPct=.1,
          quoteResponse=dict(inputMint=SOL,outputMint='token',swapMode='ExactIn',slippageBps=100,inAmount='10000000',outAmount='100',priceImpactPct='0.001',otherAmountThreshold='99',routePlan=[dict(swapInfo=dict(ammKey='pool'))]))
    def test_valid_exact_input(self):
        validate_quote(self.quote(),SOL,'token',.01)
    def test_reject_unsafe_quotes(self):
        for field,value in [('tokenOut','wrong'),('amountIn',.02),('priceImpactPct',float('nan')),('priceImpactPct',1.1),('minAmountOut',90),('maxAmountIn',.02)]:
            with self.subTest(field=field):
                q=self.quote();q[field]=value
                with self.assertRaises(ValueError): validate_quote(q,SOL,'token',.01)
        for field,value in [('swapMode','ExactOut'),('slippageBps',101),('routePlan',[]),('otherAmountThreshold','1'),('priceImpactPct','0.02')]:
            q=self.quote();q['quoteResponse'][field]=value
            with self.assertRaises(ValueError): validate_quote(q,SOL,'token',.01)
    @patch('colony.canary_executor.wallet_address',return_value=EXPECTED)
    def test_hard_limits(self,_):
        row=dict(active_ants=100,votes=80,vote_fraction=.8,hold_minutes=5,mint='token',requested_sol=.01,requested_gbp=1)
        self.assertEqual(limits(row,100,.063),.01)
        for field,value in [('votes',79),('requested_gbp',1.01),('requested_sol',.011),('hold_minutes',None),('vote_fraction',float('nan')),('votes',101)]:
            r=dict(row);r[field]=value
            with self.assertRaises(ValueError): limits(r,100,.063)
        with self.assertRaises(ValueError): limits(row,100,.05)
    @patch('colony.canary_executor.wallet_address',return_value='wrong')
    def test_wrong_wallet(self,_):
        with self.assertRaises(ValueError): limits({},100,.06)


# Real PostgreSQL tests use an isolated schema; production intents/control are untouched.
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from colony import canary_executor as executor
import db

class PostgreSQLTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        db._pool = None
        await db.init_db()
        self.namespace = 'canary_test_' + __import__('uuid').uuid4().hex
        async with db.connection() as c:
            await c.execute(f'CREATE SCHEMA {self.namespace}')
        @asynccontextmanager
        async def isolated():
            async with db.connection() as c:
                await c.execute(f'SET search_path TO {self.namespace}')
                try:
                    yield c
                finally:
                    await c.execute('SET search_path TO public')
        self.connection = isolated
        self.patches = [patch.object(executor, 'connection', isolated),
                        patch('colony.canary_controller.connection', isolated)]
        for p in self.patches: p.start()
        await executor.schema()
        async with isolated() as c:
            await c.execute('UPDATE canary_control SET stopped=false')
            self.intent = await c.fetchval('''INSERT INTO canary_trade_intents
                (candidate_id,mint,observed_at,votes,active_ants,vote_fraction,requested_gbp,
                 requested_sol,wallet_sol,wallet_gbp,status,hold_minutes)
                VALUES(1,'token',now(),80,100,.8,1,.01,.1,10,'ready',1) RETURNING id''')
        self.quote = SafetyTests().quote()
        self.mocks = [patch.object(executor,'sol_gbp_rate',return_value=(100,'kraken_public')),
                      patch.object(executor,'wallet_balance_sol',return_value=.1),
                      patch.object(executor,'wallet_address',return_value=EXPECTED),
                      patch.object(executor,'quote',return_value=self.quote),
                      patch.object(executor,'gateway',side_effect=AssertionError('broadcast forbidden'))]
        for p in self.mocks: p.start()
    async def asyncTearDown(self):
        for p in reversed(self.mocks + self.patches): p.stop()
        async with db.connection() as c:
            await c.execute(f'DROP SCHEMA {self.namespace} CASCADE')
        await db._pool.close()
        db._pool = None
    async def row(self):
        async with self.connection() as c:
            return await c.fetchrow('SELECT * FROM canary_trade_intents WHERE id=$1',self.intent)
    async def test_concurrent_claim_is_single(self):
        with patch.object(executor,'quote',return_value=self.quote) as q:
            await asyncio.gather(*(executor.tick() for _ in range(8)))
            self.assertEqual(q.call_count,1)
        r=await self.row()
        self.assertEqual(r['status'],'open')
        self.assertFalse(r['broadcast'])
    async def test_claim_survives_restart(self):
        async with self.connection() as c:
            await c.execute("UPDATE canary_trade_intents SET status='claimed',execution='{" + '"mode":"dry"' + "}'")
        await executor.tick()
        self.assertEqual((await self.row())['status'],'open')
        await executor.tick()
        self.assertEqual((await self.row())['status'],'open')
    async def test_uncertain_submission_never_retries(self):
        async with self.connection() as c:
            await c.execute("UPDATE canary_trade_intents SET status='submitting_entry',execution='{}'")
        await executor.tick(); await executor.tick()
        self.assertEqual((await self.row())['status'],'uncertain')
        async with self.connection() as c:
            control=await c.fetchrow('TABLE canary_control')
        self.assertTrue(control['stopped']); self.assertFalse(control['armed'])
    async def test_known_signature_reconciles_without_resubmit(self):
        async with self.connection() as c:
            await c.execute('UPDATE canary_trade_intents SET status=$1,execution=$2::jsonb',
                'submitting_entry',json.dumps(dict(entry_signature='sig',pending_leg='entry',mode='live')))
        tx=dict(meta=dict(err=None,preBalances=[100000000],postBalances=[90000000],
            preTokenBalances=[],postTokenBalances=[dict(owner=EXPECTED,mint='token',uiTokenAmount=dict(uiAmountString='99'))]),
            transaction=dict(message=dict(accountKeys=[EXPECTED])))
        with patch.object(executor,'rpc_call',return_value=tx): await executor.tick()
        self.assertEqual((await self.row())['status'],'open')
        await executor.tick()
    async def test_dry_exit_after_restart(self):
        await executor.tick()
        async with self.connection() as c:
            await c.execute("UPDATE canary_trade_intents SET execution=jsonb_set(execution,'{exit_at}','0')")
        await executor.tick(); await executor.tick()
        r=await self.row()
        self.assertEqual(r['status'],'closed'); self.assertFalse(r['broadcast'])
        self.assertIn('exit_quote',json.loads(r['execution']))
    async def test_stop_during_quote_prevents_open(self):
        with patch.object(executor,'quote',return_value=self.quote):
            original_thread=asyncio.to_thread
            async def thread(fn,*args):
                result=await original_thread(fn,*args)
                if fn is executor.quote:
                    async with self.connection() as c: await executor.halt(c,'test_stop')
                return result
            with patch.object(executor.asyncio,'to_thread',side_effect=thread): await executor.tick()
        self.assertEqual((await self.row())['status'],'claimed')
    async def test_live_claim_cannot_become_dry_on_restart(self):
        async with self.connection() as c:
            await c.execute('UPDATE canary_trade_intents SET status=$1,execution=$2::jsonb',
                'claimed',json.dumps(dict(mode='live')))
        await executor.tick()
        self.assertEqual((await self.row())['status'],'claimed')
    async def test_database_enforces_single_position(self):
        await executor.tick()
        async with self.connection() as c:
            with self.assertRaises(__import__('asyncpg').UniqueViolationError):
                await c.execute('''INSERT INTO canary_trade_intents
                    (candidate_id,mint,observed_at,votes,active_ants,vote_fraction,requested_gbp,
                    requested_sol,wallet_sol,wallet_gbp,status)
                    VALUES(2,'token',now(),80,100,.8,1,.01,.1,10,'open')''')

    async def test_arm_requires_completed_future_dry_run(self):
        with self.assertRaises(ValueError), patch.object(executor,'init_db',new=AsyncMock()):
            await executor.command('arm')
        async with self.connection() as c:
            self.assertFalse(await c.fetchval('SELECT armed FROM canary_control'))
    async def test_stale_claim_rejected(self):
        async with self.connection() as c:
            await c.execute("UPDATE canary_trade_intents SET status='claimed',observed_at=now()-interval '4 minutes'")
        await executor.tick()
        self.assertEqual((await self.row())['reason'],'stale')
    async def test_stop_blocks_submission(self):
        async with self.connection() as c:
            await executor.halt(c,'test_stop')
            self.assertFalse(await executor.submit(c,await self.row(),{},self.quote,'entry'))
        self.assertFalse((await self.row())['broadcast'])
    async def test_crash_after_submission_boundary_is_not_retried(self):
        async with self.connection() as c:
            await c.execute('UPDATE canary_control SET armed=true')
        with patch.object(executor,'gateway',side_effect=RuntimeError('connection lost')) as send:
            await executor.tick(); await executor.tick()
            self.assertEqual(send.call_count,1)
        r=await self.row()
        self.assertEqual(r['status'],'uncertain')
        self.assertTrue(r['broadcast'])

if __name__=='__main__': unittest.main()

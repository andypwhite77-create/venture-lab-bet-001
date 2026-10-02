import unittest
from colony.live_registry import validate_policy, strategy_family

class LiveRegistryTests(unittest.TestCase):
    def policy(self, **kw):
        p=dict(withdraw_pct=25,reinvest_pct=75,withdraw_trigger_gbp=20,reinvest_trigger_gbp=5,
               min_operating_bankroll_gbp=25,max_family_exposure_pct=40,max_ant_stake_gbp=25)
        p.update(kw); return p
    def test_profit_split_must_sum_to_100(self):
        self.assertEqual(validate_policy(self.policy())['withdraw_pct'],25)
        with self.assertRaises(ValueError): validate_policy(self.policy(withdraw_pct=20,reinvest_pct=70))
    def test_family_tags(self):
        self.assertEqual(strategy_family({'species':'deep_reversal'}),'reversal')
        self.assertEqual(strategy_family({'species':'order_flow_tempered'}),'order_flow')
    def test_limits_reject_invalid_values(self):
        with self.assertRaises(ValueError): validate_policy(self.policy(max_family_exposure_pct=101))
        with self.assertRaises(ValueError): validate_policy(self.policy(max_ant_stake_gbp=0))

if __name__=='__main__': unittest.main()

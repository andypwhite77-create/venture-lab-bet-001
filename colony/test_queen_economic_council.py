import unittest
from datetime import datetime,timezone
from colony.queen_economic_council import evaluate
T=datetime(2026,10,18,tzinfo=timezone.utc)
class Tests(unittest.TestCase):
 def test_no_profit_credit_on_small_sample(self):
  c=[{'id':1,'queen':'reversal'}]
  o=[{'confirmation_id':1,'candidate_id':1,'observed_at':T,'selected':True,'net_pct':20}]
  result=evaluate(c,o,[])
  x=result['forward_trials'][0]
  self.assertIsNone(x['earned_economic_reward'])
  self.assertFalse(x['ready_for_economic_comparison'])
  self.assertIsNone(x['descriptive_uplift_pp'])
 def test_historical_flags_never_pay(self):
  history=[{'queen':'momentum','result':{'status':'historical_discovery_only','training':{'selected_n':20,'other_n':20,'selected_mean_pct':2,'other_mean_pct':0},'chronological_mint_holdout':{'selected_n':20,'other_n':20,'selected_mean_pct':1,'other_mean_pct':0}}}]
  result=evaluate([],[],history)
  self.assertEqual(result['queens']['momentum']['historical_consistency_flags'],1)
  self.assertIsNone(result['queens']['momentum']['economic_reward'])
 def test_missing_features_excluded(self):
  c=[{'id':1,'queen':'reversal'}]
  o=[{'confirmation_id':1,'candidate_id':1,'observed_at':T,'selected':None,'net_pct':4}]
  self.assertEqual(evaluate(c,o,[])['forward_trials'][0]['missing_or_invalid_feature_rows'],1)

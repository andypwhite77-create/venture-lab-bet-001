import unittest
from datetime import datetime,timedelta,timezone
from colony.ant_plasticity_shadow import evaluate
class Tests(unittest.TestCase):
 def test_future_outcomes_cannot_affect_previous_decision(self):
  t=datetime(2026,1,1,tzinfo=timezone.utc)
  entries=[{'entry_id':i,'genome_id':'A','observed_at':t+timedelta(minutes=i)} for i in range(1,7)]
  marks={'A':[{'entry_id':i,'outcome_at':t+timedelta(minutes=i,seconds=1),'net_pct':-12} for i in range(1,5)]}
  r=evaluate(entries,marks)
  self.assertEqual(r[0]['shadow_action'],'follow_dna')
  self.assertEqual(r[4]['shadow_action'],'abstain')
 def test_positive_history_leaves_dna_untouched(self):
  t=datetime(2026,1,1,tzinfo=timezone.utc)
  entries=[{'entry_id':9,'genome_id':'A','observed_at':t+timedelta(hours=2)}]
  marks={'A':[{'entry_id':i,'outcome_at':t+timedelta(minutes=i),'net_pct':2} for i in range(5)]}
  self.assertEqual(evaluate(entries,marks)[0]['shadow_action'],'follow_dna')

class RegimeTests(unittest.TestCase):
 def test_missing_features_remain_unknown(self):
  from colony.ant_plasticity_shadow import regime
  self.assertEqual(regime({}),'unknown')
 def test_thin_liquidity_classified_from_entry_data(self):
  from colony.ant_plasticity_shadow import regime
  self.assertEqual(regime({'liquidity_usd':10000,'price_change_m5':2}),'thin_liquidity')
 def test_outdated_losses_decay_back_to_baseline(self):
  t=datetime(2026,1,3,tzinfo=timezone.utc)
  marks={'A':[{'entry_id':i,'outcome_at':t-timedelta(hours=100-i),'net_pct':-7} for i in range(5)]}
  entry=[{'entry_id':10,'genome_id':'A','observed_at':t,'features':{'liquidity_usd':100000,'price_change_m5':1}}]
  self.assertEqual(evaluate(entry,marks)[0]['shadow_action'],'follow_dna')

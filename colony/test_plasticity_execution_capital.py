import unittest
from datetime import datetime,timedelta,timezone
from colony.plasticity_execution_capital import compare
T=datetime(2026,10,15,tzinfo=timezone.utc)
def row(i,latency):
 return {'entry_id':i,'genome_id':'g','entry_at':T+timedelta(minutes=20*i),'stake_gbp':25,
 'action':'follow_dna','outcome_at':T+timedelta(minutes=20*i+15),
 'captured_at':T+timedelta(minutes=20*i+15),'net_return_pct':10,
 'entry_status':'quoted','exit_status':'quoted','entry_latency':.1,'exit_latency':latency}
class StressTest(unittest.TestCase):
 def test_delayed_exit_does_not_credit_profit(self):
  x=compare([row(1,40)])
  self.assertGreater(x['diagnostic_mark_model']['arms']['fixed_dna']['total_closed_pnl_gbp'],0)
  self.assertEqual(x['timely_quote_only_stress']['arms']['fixed_dna']['total_closed_pnl_gbp'],0)
  self.assertEqual(x['timely_quote_only_stress']['arms']['fixed_dna']['per_genome'][0]['locked_unmarked_gbp'],25)
 def test_timely_mark_remains_unverified(self):
  x=compare([row(1,.2)])
  self.assertEqual(x['evidence_counts']['timely_pair_not_fill'],1)
  self.assertGreater(x['timely_quote_only_stress']['arms']['fixed_dna']['total_closed_pnl_gbp'],0)

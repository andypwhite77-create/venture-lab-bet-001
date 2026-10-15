import unittest
from datetime import datetime,timedelta,timezone
from colony.plasticity_capital_daily import replay
T=datetime(2026,10,15,tzinfo=timezone.utc)
def row(i,minutes,ret,action='follow_dna',captured=None):
 return {'entry_id':i,'genome_id':'g','entry_at':T+timedelta(minutes=minutes),'stake_gbp':25,
 'action':action,'outcome_at':T+timedelta(minutes=minutes+15) if ret is not None else None,
 'captured_at':T+timedelta(minutes=minutes+15) if ret is not None else None,'net_return_pct':ret}
class CapitalTests(unittest.TestCase):
 def test_overlapping_positions_cannot_double_spend(self):
  x=replay([row(1,0,5),row(2,1,5)])['arms']['fixed_dna'];self.assertEqual(x['per_genome'][0]['no_cash'],1)
 def test_abstain_prevents_loss(self):
  x=replay([row(1,0,-50,'abstain')])['arms'];self.assertEqual(x['plasticity']['total_closed_pnl_gbp'],0);self.assertLess(x['fixed_dna']['total_closed_pnl_gbp'],0)
 def test_pending_capital_locked(self):
  x=replay([row(1,0,None),row(2,40,10)])['arms']['fixed_dna'];self.assertEqual(x['per_genome'][0]['no_cash'],1);self.assertEqual(x['per_genome'][0]['locked_unmarked_gbp'],25)
 def test_negative_cash_prevented(self):
  x=replay([row(1,0,-200)])['arms']['fixed_dna'];self.assertGreaterEqual(x['per_genome'][0]['cash_gbp'],0)
if __name__=='__main__':unittest.main()

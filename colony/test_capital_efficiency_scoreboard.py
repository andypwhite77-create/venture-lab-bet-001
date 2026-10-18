import unittest
from datetime import datetime,timedelta,timezone
from colony.capital_efficiency_scoreboard import score
T=datetime(2026,10,18,tzinfo=timezone.utc)
def row(n,action,amount,minute,key=1,accepted=True):return {'source_event_id':n,'genome_id':'g','source_entry_id':key,'action':action,'amount_lamports':amount,'accepted':accepted,'decided_at':T+timedelta(minutes=minute)}
class CapitalScoreboardTests(unittest.TestCase):
 def test_profit_and_capital_hours(self):
  r=score([row(1,'reserve',50,0),row(2,'release',55,60)],T+timedelta(hours=2),100)['g']
  self.assertEqual(r['realized_hypothetical_net_sol'],.000000005)
  self.assertEqual(r['locked_capital_sol_hours'],.00000005)
  self.assertEqual(r['pending_positions'],0)
 def test_missing_exit_remains_locked(self):
  r=score([row(1,'reserve',50,0)],T+timedelta(hours=2),100)['g']
  self.assertEqual(r['locked_sol'],.00000005)
  self.assertFalse(r['eligible_for_comparison'])
 def test_rejected_event_not_funded(self):
  r=score([row(1,'reserve',150,0,accepted=False)],T+timedelta(hours=1),100)['g']
  self.assertEqual(r['available_sol'],.0000001)
  self.assertEqual(r['rejected_events'],1)
 def test_invalid_accepted_release_fails(self):
  with self.assertRaises(ValueError):score([row(1,'release',50,0)],T,100)

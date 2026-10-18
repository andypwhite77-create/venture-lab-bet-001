import unittest
from datetime import datetime,timedelta,timezone
from colony.capital_reconciliation import reconcile
class CapitalTests(unittest.TestCase):
 def test_unfunded_reserve_does_not_create_cash(self):
  t=datetime.now(timezone.utc)
  rows=[dict(genome_id='g',source_entry_id=1,action='reserve',amount_lamports=90000000,event_at=t),dict(genome_id='g',source_entry_id=2,action='reserve',amount_lamports=90000000,event_at=t+timedelta(seconds=1)),dict(genome_id='g',source_entry_id=2,action='release',amount_lamports=150000000,event_at=t+timedelta(seconds=2))]
  result=reconcile(rows)['g']
  self.assertEqual(result['available_lamports'],10000000)
  self.assertEqual(result['locked_lamports'],90000000)
  self.assertEqual(result['rejected_events'],2)
 def test_release_only_after_reserve(self):
  t=datetime.now(timezone.utc)
  rows=[dict(genome_id='g',source_entry_id=1,action='reserve',amount_lamports=10000000,event_at=t),dict(genome_id='g',source_entry_id=1,action='release',amount_lamports=11000000,event_at=t+timedelta(seconds=10))]
  result=reconcile(rows)['g']
  self.assertEqual(result['available_lamports'],101000000)
  self.assertEqual(result['locked_lamports'],0)

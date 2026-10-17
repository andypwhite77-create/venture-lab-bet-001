import unittest
from datetime import datetime,timedelta,timezone
from colony.quote_to_quote_ledger import assess
class LedgerTests(unittest.TestCase):
 def test_unresolved_position_locks_cash(self):
  t=datetime.now(timezone.utc)
  q={'in_amount':'10000000','out_amount':'1000','route_labels':['AMM']}
  row={'id':1,'genome_id':'a','observed_at':t,'exit_due':t+timedelta(minutes=5),'entry_status':'quoted','entry_latency':1,'entry_quote':q,'exit_status':'unavailable','exit_latency':1,'exit_quote':None}
  result=assess([row])['genomes']['a']
  self.assertEqual(result['available_book_cash_sol'],.09)
  self.assertEqual(result['unresolved_reserved_sol'],.01)
  self.assertEqual(result['quote_pairs'],0)
 def test_quote_pair_net_in_sol(self):
  t=datetime.now(timezone.utc)
  entry={'in_amount':'10000000','out_amount':'1000','route_labels':['AMM']}
  exit={'in_amount':'1000','out_amount':'11000000','route_labels':['AMM']}
  row={'id':2,'genome_id':'b','observed_at':t,'exit_due':t+timedelta(minutes=5),'entry_status':'quoted','entry_latency':1,'entry_quote':entry,'exit_status':'quoted','exit_latency':1,'exit_quote':exit}
  result=assess([row])['genomes']['b']
  self.assertEqual(result['quote_pairs'],1)
  self.assertAlmostEqual(result['net_quote_sol'],.001)

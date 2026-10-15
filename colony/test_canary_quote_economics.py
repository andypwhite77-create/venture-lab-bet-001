import unittest
from colony.canary_quote_economics import evaluate
class QuoteEconomicsTests(unittest.TestCase):
 def test_exact_token_quantity_required(self):
  r={'entry_id':1,'entry_quote':{'in_amount':'10000000','out_amount':'200'},
     'exit_quote':{'in_amount':'199','out_amount':'10500000'},'entry_latency':1,'exit_latency':2}
  self.assertEqual(evaluate([r]),[])
 def test_cost_deducted_from_round_trip(self):
  r={'entry_id':1,'entry_quote':{'in_amount':'10000000','out_amount':'200'},
     'exit_quote':{'in_amount':'200','out_amount':'10000000'},'entry_latency':1,'exit_latency':2}
  self.assertLess(evaluate([r])[0]['net_pct'],0)

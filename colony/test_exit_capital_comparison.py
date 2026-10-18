import unittest
from datetime import datetime,timedelta,timezone
from colony.exit_capital_comparison import compare
T=datetime(2026,10,18,tzinfo=timezone.utc)
def row(i,minute,net=2,complete=True):
 outcome={p:{'status':'observed_path','exit_at':(T+timedelta(minutes=minute+20)).isoformat(),'net_pct':net} for p in ('control','take_10','stop_10_take_15')}
 if not complete:outcome['take_10']={'status':'insufficient_path'}
 return {'candidate_id':i,'entry_at':T+timedelta(minutes=minute),'outcome':outcome}
class Tests(unittest.TestCase):
 def test_equal_policy_and_settlement(self):
  result=compare([row(1,0)],T+timedelta(hours=1))
  for p in result['policies'].values():
   self.assertEqual(p['completed'],1);self.assertEqual(p['pending'],0)
   self.assertEqual(p['realized_hypothetical_net_sol'],.0002)
 def test_incomplete_path_excluded_everywhere(self):
  r=compare([row(1,0,complete=False)],T+timedelta(hours=1))
  self.assertTrue(all(v['completed']==0 and v['excluded_missing_path']==1 for v in r['policies'].values()))
 def test_unmatured_position_locked(self):
  r=compare([row(1,0)],T+timedelta(minutes=10))['policies']['control']
  self.assertEqual(r['pending'],1);self.assertEqual(r['realized_hypothetical_net_sol'],0)

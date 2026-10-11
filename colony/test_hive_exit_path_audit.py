import unittest
from datetime import datetime,timedelta,timezone
from colony.hive_exit_path_audit import simulate
class PathExitTests(unittest.TestCase):
 def setUp(self):self.t=datetime(2026,10,11,tzinfo=timezone.utc)
 def test_stop_fires_before_take(self):
  result=simulate(self.t,100,[(self.t,100),(self.t+timedelta(minutes=1),92),(self.t+timedelta(minutes=2),120),(self.t+timedelta(minutes=5),101)],5,-5,10)
  self.assertEqual(result['exit_reason'],'stop');self.assertAlmostEqual(result['net_pct'],-8.3)
 def test_take_fires(self):
  r=simulate(self.t,100,[(self.t,100),(self.t+timedelta(minutes=1),112),(self.t+timedelta(minutes=5),90)],5,-5,10)
  self.assertEqual(r['exit_reason'],'take')
 def test_gap_rejected(self):
  r=simulate(self.t,100,[(self.t,100),(self.t+timedelta(minutes=25),90),(self.t+timedelta(minutes=30),80)],30,-5,10)
  self.assertEqual(r['status'],'insufficient_path')

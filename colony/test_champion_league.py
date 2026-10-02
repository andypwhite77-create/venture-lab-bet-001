import unittest
from datetime import datetime,timezone,timedelta
from colony.champion_league import _score,_behaviour_signature,_cooldown_remaining

class ChampionLeagueTests(unittest.TestCase):
 def test_score_rewards_consistent_positive_returns(self):
  good=_score([2,2,2,2,2]);mixed=_score([8,-8,8,-8,0])
  self.assertGreater(good['score'],mixed['score'])
 def test_score_reports_lower_confidence_bound(self):
  x=_score([1,2,3,4,5])
  self.assertLess(x['lcb'],x['mean'])
 def test_behaviour_signature_changes_with_hold(self):
  a={'parameters':{'hold_minutes':5}};b={'parameters':{'hold_minutes':15}}
  self.assertNotEqual(_behaviour_signature(['A','B'],a),_behaviour_signature(['A','B'],b))
 def test_promotion_cooldown_slows_roster_churn(self):
  now=datetime(2026,10,2,tzinfo=timezone.utc)
  self.assertEqual(_cooldown_remaining(None,now,259200),0)
  self.assertGreater(_cooldown_remaining(now-timedelta(days=1),now,259200),0)
  self.assertEqual(_cooldown_remaining(now-timedelta(days=4),now,259200),0)

if __name__=='__main__':unittest.main()

import unittest
from colony.champion_league import _score,_behaviour_signature

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

if __name__=='__main__':unittest.main()

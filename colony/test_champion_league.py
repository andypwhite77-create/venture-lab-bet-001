import unittest
from datetime import datetime,timezone,timedelta
from colony.champion_league import _score,_behaviour_signature,_cooldown_remaining,_retirement_reason,_cap_qualification_behaviours,MAX_QUALIFICATION_DAYS,MIN_FORWARD_EVENTS

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



 def test_behaviour_cap_keeps_top_two(self):
  qs=[{'genome_id':'a','sig':'x','total':3},{'genome_id':'b','sig':'x','total':2},{'genome_id':'c','sig':'x','total':1},{'genome_id':'d','sig':'y','total':0}]
  keep,retire=_cap_qualification_behaviours(qs,2)
  self.assertEqual([x['genome_id'] for x in keep],['a','b','d'])
  self.assertEqual([x['genome_id'] for x in retire],['c'])

 def test_training_budget_retirement(self):
  self.assertIsNone(_retirement_reason(MAX_QUALIFICATION_DAYS-1,0,-99,-1))
  self.assertEqual(_retirement_reason(MAX_QUALIFICATION_DAYS,MIN_FORWARD_EVENTS-1,5,-1),'training_budget_expired_insufficient_forward_evidence')
  self.assertEqual(_retirement_reason(MAX_QUALIFICATION_DAYS,MIN_FORWARD_EVENTS,-2,-1),'training_budget_expired_below_incumbent')
  self.assertIsNone(_retirement_reason(MAX_QUALIFICATION_DAYS,MIN_FORWARD_EVENTS,1,-1))

if __name__=='__main__':unittest.main()

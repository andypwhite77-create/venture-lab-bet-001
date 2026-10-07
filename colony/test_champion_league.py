import unittest
from datetime import datetime,timezone,timedelta
from colony.champion_league import _score,_behaviour_signature,_cooldown_remaining,_retirement_reason,_cap_qualification_behaviours,_historical_priority,_priority_sort_key,_passes_canary_paper_gate,_challenger_beats_canary,MAX_QUALIFICATION_DAYS,MIN_FORWARD_EVENTS

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


 def test_promotion_has_reliability_gates(self):
  import inspect,colony.champion_league as cl
  src=inspect.getsource(cl.refresh_rankings)
  self.assertIn('MIN_PROMOTION_WIN_RATE',src)
  self.assertIn('MAX_PROMOTION_SINGLE_LOSS_PCT',src)
  self.assertIn('MIN_PROMOTION_MEDIAN_PCT',src)
  self.assertIn('MIN_PROMOTION_POSITIVE_DAY_RATE',src)


 def test_historical_priority_rewards_robust_history_without_changing_promotion(self):
  self.assertEqual(_historical_priority({'n':33,'mean':5.18,'median':2.69,'win_rate':.788,'worst':-9.57,'lcb':2.92}),'A+')
  self.assertEqual(_historical_priority({'n':53,'mean':5.92,'median':3.91,'win_rate':.642,'worst':-28.8,'lcb':2.67}),'A')
  self.assertIsNone(_historical_priority({'n':64,'mean':4.36,'median':6.5,'win_rate':.578,'worst':-88.5,'lcb':.27}))
  self.assertIsNone(_historical_priority({'n':10,'mean':16,'median':6,'win_rate':.8,'worst':-2.8,'lcb':3}))

 def test_priority_order_services_a_plus_then_a_then_normal(self):
  rows=[
   {'genome_id':'z','notes':{}},
   {'genome_id':'b','notes':{'historical_priority_tier':'A'}},
   {'genome_id':'a','notes':{'historical_priority_tier':'A+'}},
  ]
  self.assertEqual([r['genome_id'] for r in sorted(rows,key=_priority_sort_key)],['a','b','z'])


 def test_canary_gate_requires_25_fresh_reliable_trades(self):
  good={'forward':{'n':25,'days':3,'win_rate':.60,'worst':-10,'median':1.0,'positive_day_rate':.67,'score':2},
        'arena':{'score':1},'total':1.5}
  self.assertTrue(_passes_canary_paper_gate(good))
  bad={**good,'forward':{**good['forward'],'n':24}}
  self.assertFalse(_passes_canary_paper_gate(bad))

 def test_upstart_must_beat_canary_forward_total_and_arena(self):
  incumbent={'forward':{'n':80,'days':8,'win_rate':.55,'worst':-20,'median':.3,'positive_day_rate':.7,'score':1},
             'arena':{'score':1},'total':1}
  challenger={'forward':{'n':25,'days':3,'win_rate':.65,'worst':-10,'median':1,'positive_day_rate':.8,'score':2},
              'arena':{'score':2},'total':2}
  self.assertTrue(_challenger_beats_canary(challenger,incumbent))
  challenger['total']=.5
  self.assertFalse(_challenger_beats_canary(challenger,incumbent))


 def test_canary_members_are_protected_from_generic_qualification_culls(self):
  import inspect,colony.champion_league as cl
  src=inspect.getsource(cl.refresh_rankings)
  self.assertIn("protected_dupes=[q for q in duplicate_retire if q['genome_id'] in canary_ids]",src)
  self.assertIn("if q['genome_id'] in canary_ids: continue",src)

 def test_training_budget_retirement(self):
  self.assertIsNone(_retirement_reason(MAX_QUALIFICATION_DAYS-1,0,-99,-1))
  self.assertEqual(_retirement_reason(MAX_QUALIFICATION_DAYS,MIN_FORWARD_EVENTS-1,5,-1),'training_budget_expired_insufficient_forward_evidence')
  self.assertEqual(_retirement_reason(MAX_QUALIFICATION_DAYS,MIN_FORWARD_EVENTS,-2,-1),'training_budget_expired_below_incumbent')
  self.assertIsNone(_retirement_reason(MAX_QUALIFICATION_DAYS,MIN_FORWARD_EVENTS,1,-1))

if __name__=='__main__':unittest.main()

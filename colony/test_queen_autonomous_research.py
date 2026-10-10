import unittest
from colony.queen_autonomous_research import validate

SNAP={'source_tables':['canary_trade_intents'],'canary_intents':{'total':10,'route_blocked':3}}
class CouncilTests(unittest.TestCase):
 def test_unsupported_short_not_promoted(self):
  p={'kind':'major_asset_short','title':'Huge token repricing',
     'thesis':'Public-data hypothesis not independently verified and based on limited historical records',
     'failure_modes':['squeeze']}
  self.assertIsNone(validate(p,{'research_appropriate':True,'objections':['unverified']},SNAP))
 def test_critical_veto(self):
  p={'kind':'market_dislocation','title':'Examine missing routes',
     'thesis':'Explore whether unavailable routes predict high subsequent trading losses',
     'failure_modes':['sampling']}
  self.assertIsNone(validate(p,{'research_appropriate':False,'objections':['selection bias']},SNAP))
 def test_critique_preserved(self):
  p={'kind':'market_dislocation','title':'Examine missing routes',
     'thesis':'Explore whether unavailable routes predict high subsequent trading losses',
     'failure_modes':['sampling']}
  out=validate(p,{'research_appropriate':True,'objections':['selection bias']},SNAP)
  self.assertEqual(out['risks'],['sampling','selection bias'])
  self.assertEqual(out['resources']['scope'],'human-approved research only; no trading or subscriptions')

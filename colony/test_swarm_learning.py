import unittest
from colony.swarm_queen import _bounded_research_plan

class SwarmLearningTests(unittest.TestCase):
    def base(self):
        return {'queen_research':{
            'largest_behaviour_fraction':.1,'behaviour_groups':30,'behaviour_hhi':.05,
            'behaviour_entropy':.9,'effective_behaviours':25,'spartan_drought_campaigns':0,
            'sensor_availability':{'price_change_h1':1.0,'price_change_m5':1.0},
            'career_preferred_features':['price_change_h1'],'preferred_features':['price_change_m5']}}

    def test_drought_forces_search_diversity(self):
        e=self.base();e['queen_research']['spartan_drought_campaigns']=5
        p=_bounded_research_plan({},e)
        self.assertGreaterEqual(p['wild_scouts'],.35)
        self.assertGreaterEqual(p['adjacent_explore'],.30)

    def test_bounded_strategy_can_focus_but_not_invent_sensor(self):
        e=self.base();e['strategic_guidance']={'research_adjustments':{
            'mode':'diversify','focus_sensors':['price_change_m5','not_a_sensor'],'avoid_sensors':[]}}
        p=_bounded_research_plan({},e)
        self.assertEqual(p['strategic_mode'],'diversify')
        self.assertIn('price_change_m5',p['focus_sensors'])
        self.assertNotIn('not_a_sensor',p['focus_sensors'])

if __name__=='__main__': unittest.main()

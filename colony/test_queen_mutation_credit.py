import unittest
from colony import queen_mutation_credit as q

class MutationCreditTests(unittest.TestCase):
    def test_weights_are_bounded_and_normalized(self):
        state=q._blank(); w=q.weights(state)
        self.assertAlmostEqual(sum(w.values()),1.0,places=9)
        self.assertEqual(set(w),set(q.OPERATORS))
        self.assertTrue(all(v>=q.FLOOR for v in w.values()))

    def test_repeated_improvement_earns_more_weight(self):
        state=q._blank()
        for _ in range(40): state=q.record('local',-.5,-.3,state)
        for _ in range(40): state=q.record('wide',-.5,-999,state)
        w=q.weights(state)
        self.assertGreater(w['local'],w['standard'])
        self.assertGreater(w['standard'],w['wide'])


    def test_recent_results_can_override_stale_lifetime_history(self):
        state=q._blank()
        for k in q.OPERATORS:
            state['operators'][k].update(trials=1000000,wins=100000,delta_sum=-250000.0)
        state['operators']['local']['recent']=[{'delta':0.15,'win':True} for _ in range(200)]
        state['operators']['wide']['recent']=[{'delta':-1.0,'win':False} for _ in range(200)]
        w=q.weights(state)
        self.assertGreater(w['local'],w['standard'])
        self.assertGreater(w['standard'],w['wide'])
        self.assertGreaterEqual(w['wide'],q.FLOOR)

    def test_bad_child_is_negative_credit(self):
        state=q.record('standard',-.4,-999,q._blank())
        z=state['operators']['standard']
        self.assertEqual(z['trials'],1)
        self.assertEqual(z['wins'],0)
        self.assertLess(z['delta_sum'],0)

if __name__=='__main__': unittest.main()

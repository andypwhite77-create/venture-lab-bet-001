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

    def test_bad_child_is_negative_credit(self):
        state=q.record('standard',-.4,-999,q._blank())
        z=state['operators']['standard']
        self.assertEqual(z['trials'],1)
        self.assertEqual(z['wins'],0)
        self.assertLess(z['delta_sum'],0)

if __name__=='__main__': unittest.main()

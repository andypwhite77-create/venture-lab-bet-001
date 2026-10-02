import random
import unittest

from colony.queen_pattern_recognition import random_genome, selection_fitness


def metrics(n, score=1.0, outlier=.20):
    return {
        'n': n, 'avg_net_gbp': 1.0, 'nursery_score': score,
        'outlier': outlier, 'win_rate': .60,
        'low_age_fraction': 0.0, 'low_liquidity_fraction': 0.0,
    }


class QueenQualityTests(unittest.TestCase):
    def test_breadth_beats_threshold_hugging(self):
        genome = {'predicates': {'a': {'min': 1}}}
        thin = selection_fitness([metrics(18), metrics(12)], genome)
        broad = selection_fitness([metrics(60), metrics(30)], genome)
        self.assertGreater(broad, thin)

    def test_floor_preserves_viable_funnel(self):
        genome = {'predicates': {'a': {'min': 1}}}
        self.assertGreater(selection_fitness([metrics(18), metrics(12)], genome), -900)
        self.assertLess(selection_fitness([metrics(17), metrics(12)], genome), -900)
        self.assertLess(selection_fitness([metrics(18), metrics(11)], genome), -900)

    def test_parsimony_penalises_needless_complexity(self):
        parts = [metrics(60), metrics(30)]
        simple = {'predicates': {str(i): {'min': 1} for i in range(3)}}
        complex_ = {'predicates': {str(i): {'min': 1} for i in range(5)}}
        self.assertGreater(selection_fitness(parts, simple), selection_fitness(parts, complex_))

    def test_random_genomes_stay_simple_enough_to_explore(self):
        rng = random.Random(123)
        for _ in range(500):
            genome = random_genome(rng, {}, {'exploit': .0, 'adjacent_explore': .0, 'wild_scouts': 1.0, 'top_niches': []}, {})
            self.assertGreaterEqual(len(genome['predicates']), 1)
            self.assertLessEqual(len(genome['predicates']), 4)


if __name__ == '__main__':
    unittest.main()

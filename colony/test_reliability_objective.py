import unittest
from colony.reversal_tournament import score_record

class ReliabilityObjectiveTests(unittest.TestCase):
    def test_shorter_hold_gets_only_small_efficiency_bonus(self):
        vals=[('a',1.0),('b',1.0),('c',1.0),('d',1.0),('e',1.0),('f',1.0),('g',1.0),('h',1.0)]
        a=score_record(vals,{},hold_minutes=5)
        b=score_record(vals,{},hold_minutes=30)
        self.assertGreater(a['efficiency_bonus'],b['efficiency_bonus'])
        self.assertLessEqual(abs(a['efficiency_bonus']),0.04)
    def test_tail_is_penalised(self):
        steady=[('a',1),('b',1),('c',1),('d',1),('e',1),('f',1),('g',1),('h',1)]
        ugly=[('a',6),('b',6),('c',6),('d',6),('e',6),('f',6),('g',6),('h',-35)]
        self.assertGreater(score_record(steady,{},hold_minutes=5)['tournament_score'],
                           score_record(ugly,{},hold_minutes=5)['tournament_score'])

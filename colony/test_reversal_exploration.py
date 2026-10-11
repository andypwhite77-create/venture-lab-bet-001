import unittest
from colony.reversal_exploration import frozen_agents
from colony.genome import genome_id
class NoveltyTests(unittest.TestCase):
 def test_quarantine_and_entry_diversity(self):
  ants=frozen_agents();self.assertEqual(len(ants),5)
  self.assertEqual(sum(int(b) for _,b in ants),1)
  self.assertEqual(len({genome_id(g) for g,_ in ants}),5)
  self.assertEqual(len({tuple(sorted(g['predicates'])) for g,_ in ants}),5)
  self.assertTrue(all(g['research_only'] for g,_ in ants))

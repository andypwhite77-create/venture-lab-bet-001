import unittest
from colony.queen_roles import BREEDING_QUEEN, SWARM_QUEEN, ROLE_VERSION, snapshot

class QueenRoleTests(unittest.TestCase):
    def test_breeding_queen_is_only_genome_factory(self):
        self.assertEqual(BREEDING_QUEEN['authority'],'sole_genome_factory')
        self.assertIn('breed_and_mutate_genomes',BREEDING_QUEEN['responsibilities'])
        self.assertEqual(BREEDING_QUEEN['qualification_handoff'],2)

    def test_swarm_is_research_director_not_breeder(self):
        self.assertEqual(SWARM_QUEEN['authority'],'research_director')
        self.assertIn('spawn_genomes',SWARM_QUEEN['forbidden'])
        self.assertIn('mutate_genomes',SWARM_QUEEN['forbidden'])
        self.assertIn('directly_promote_challengers',SWARM_QUEEN['forbidden'])

    def test_second_market_requires_model_review(self):
        s=snapshot()
        self.assertEqual(s['version'],ROLE_VERSION)
        self.assertEqual(s['next_market_candidate'],'ethereum')
        self.assertEqual(SWARM_QUEEN['model_upgrade_trigger'],'before_second_market_activation')

if __name__=='__main__': unittest.main()

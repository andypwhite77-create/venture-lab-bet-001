import unittest
from colony.evidence import assess

class EvidenceTests(unittest.TestCase):
    def test_blocks_thin_evidence(self):
        c={'comparison_evidence_mints':3,'evolved_minus_blind_pct':20}
        s={'objections':['insufficient_independent_opportunities']}
        a=assess(c,s)
        self.assertFalse(a['eligible_for_scout_proposal'])
        self.assertFalse(a['eligible_for_generation_change'])

    def test_scout_before_generation(self):
        c={'comparison_evidence_mints':12,'evolved_minus_blind_pct':2}
        s={'objections':[]}
        a=assess(c,s)
        self.assertTrue(a['eligible_for_scout_proposal'])
        self.assertFalse(a['eligible_for_generation_change'])

    def test_generation_requires_clear_edge(self):
        c={'comparison_evidence_mints':35,'evolved_minus_blind_pct':6}
        s={'objections':[]}
        self.assertTrue(assess(c,s)['eligible_for_generation_change'])

if __name__=='__main__': unittest.main()

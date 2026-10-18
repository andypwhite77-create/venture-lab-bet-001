import unittest
from datetime import datetime,timezone
from colony.queen_funded_attribution import audit
T=datetime(2026,10,18,tzinfo=timezone.utc)
def reserve(gid):return {'genome_id':gid,'source_event_id':1,'source_entry_id':9,'action':'reserve','amount_lamports':10000000,'accepted':True,'decided_at':T}
class Tests(unittest.TestCase):
 def test_unknown_genome_stays_unassigned(self):
  result=audit([reserve('missing')],[],T)
  self.assertEqual(result['unmapped_count'],1)
  self.assertEqual(result['families'],{})
  self.assertIsNone(result['economic_rewards'])
 def test_known_genome_attributed(self):
  result=audit([reserve('known')],[{'genome_id':'known','family':'reversal'}],T)
  self.assertEqual(result['matched_genomes'],1)
 def test_conflicting_family_fails_closed(self):
  result=audit([reserve('known')],[{'genome_id':'known','family':'reversal'},{'genome_id':'known','family':'momentum'}],T)
  self.assertEqual(result['unmapped_count'],1)

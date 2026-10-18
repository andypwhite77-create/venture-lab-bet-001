import unittest
from datetime import datetime,timezone
from colony.queen_funded_attribution import audit
T=datetime(2026,10,18,tzinfo=timezone.utc)
def reserve(gid):return {'genome_id':gid,'source_event_id':1,'source_entry_id':9,'action':'reserve','amount_lamports':10000000,'accepted':True,'decided_at':T}
def source(gid,family):return [{'genome_id':gid,'family':family}]
class Tests(unittest.TestCase):
 def test_missing_provenance_fails_closed(self):
  r=audit([reserve('unknown')],[],T)
  self.assertEqual(r['unmapped_count'],1)
  self.assertIsNone(r['economic_rewards'])
 def test_two_sources_agree(self):
  r=audit([reserve('known')],[],T,source('known','reversal'),source('known','reversal'))
  self.assertEqual(r['matched_genomes'],1)
  self.assertIn('reversal',r['families'])
 def test_conflict_fails_closed(self):
  r=audit([reserve('known')],source('known','momentum'),T,source('known','reversal'),source('known','reversal'))
  self.assertEqual(r['unmapped_count'],1)
 def test_single_source_cannot_assign(self):
  r=audit([reserve('known')],source('known','reversal'),T)
  self.assertEqual(r['matched_genomes'],0)

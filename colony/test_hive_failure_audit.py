import unittest
from colony.hive_failure_audit import diagnose
class FailureAuditTests(unittest.TestCase):
 def test_empty(self):self.assertEqual(diagnose([])['status'],'no_matched_evidence')
 def test_count_unique_opportunities(self):
  rows=[{'opportunity_id':'a','challenger_genome_id':'1'},{'opportunity_id':'a','challenger_genome_id':'2'},{'opportunity_id':'b','challenger_genome_id':'1'}]
  self.assertEqual(diagnose(rows)['opportunity_count'],2)

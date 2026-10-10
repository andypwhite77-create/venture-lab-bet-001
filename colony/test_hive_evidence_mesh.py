import unittest
from colony.hive_evidence_mesh import grade_value
class MeshEvidenceTests(unittest.TestCase):
 def test_evidence_hierarchy(self):self.assertLess(grade_value('hypothesis'),grade_value('realized_live'))
 def test_grade_rejects_unbounded_level(self):
  with self.assertRaises(ValueError):grade_value('absolute_truth')

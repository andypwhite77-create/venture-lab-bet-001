import inspect
import unittest
import research_db


class ResearchOutcomeRequestSQLTests(unittest.TestCase):
    def test_requested_horizon_is_explicitly_integer_typed(self):
        src = inspect.getsource(research_db.request_candidate_outcome)
        self.assertIn("$2::int", src)
        self.assertIn("$2::int * INTERVAL '1 minute'", src)


if __name__ == "__main__":
    unittest.main()

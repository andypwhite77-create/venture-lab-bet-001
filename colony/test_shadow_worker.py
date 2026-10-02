import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from colony import shadow_worker


class FakeConn:
    def __init__(self, t0):
        self.t0 = t0
        self.fetch_calls = []
        self.exec_calls = []

    async def fetch(self, sql, *args):
        self.fetch_calls.append((sql, args))
        if 'FROM colony_shadow_descendants' in sql:
            return [{'id': 7, 'genome': {'parameters': {'hold_minutes': 15}}, 'evidence_cutoff': 10}]
        if 'FROM research_candidates' in sql:
            return [
                {'id': 11, 'created_at': self.t0, 'mint': 'A', 'features': {}, 'market': {}},
                {'id': 12, 'created_at': self.t0 + timedelta(minutes=30), 'mint': 'A', 'features': {}, 'market': {}},
            ]
        if 'FROM colony_shadow_entries' in sql and 'GROUP BY' in sql:
            return []
        raise AssertionError(sql)

    async def fetchval(self, sql, *args):
        if 'last_candidate_id' in sql:
            return None
        raise AssertionError(sql)

    async def execute(self, sql, *args):
        self.exec_calls.append((sql, args))
        if 'INSERT INTO colony_shadow_entries' in sql:
            return 'INSERT 0 1'
        return 'OK'


class ShadowWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_state_is_prefetched_and_updated_in_memory(self):
        t0 = datetime.now(timezone.utc)
        conn = FakeConn(t0)
        seen_prev = []

        @asynccontextmanager
        async def fake_connection():
            yield conn

        def fake_eligible(genome, row, prev):
            seen_prev.append(prev)
            return True

        with patch.object(shadow_worker, 'connection', fake_connection), patch.object(shadow_worker, 'eligible', fake_eligible):
            result = await shadow_worker.process_shadow()

        self.assertEqual(result, {'descendants': 1, 'candidates_considered': 2, 'inserted': 2})
        self.assertEqual(seen_prev, [None, t0])
        self.assertEqual(len(conn.fetch_calls), 3)
        self.assertTrue(any('INSERT INTO colony_candidate_progress' in sql for sql, _ in conn.exec_calls))
        self.assertTrue(any('UPDATE colony_candidate_progress' in sql for sql, _ in conn.exec_calls))
        self.assertFalse(any('SELECT max(observed_at)' in sql for sql, _ in conn.fetch_calls))


if __name__ == '__main__':
    unittest.main()

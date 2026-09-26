"""Persistent experience for Queen/Sceptic; memory is evidence, never authority."""
import json
from db import connection

async def ensure_schema():
    async with connection() as c:
        await c.execute('''CREATE TABLE IF NOT EXISTS colony_mind_memory(
          id BIGSERIAL PRIMARY KEY, run_id TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT now(),
          kind TEXT NOT NULL, subject TEXT, lesson TEXT NOT NULL, evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
          confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5, source_journal_id BIGINT,
          outcome TEXT NOT NULL DEFAULT 'unresolved')''')
        await c.execute('CREATE INDEX IF NOT EXISTS colony_mind_memory_run_kind ON colony_mind_memory(run_id,kind,created_at DESC)')

async def remember(run_id,kind,lesson,evidence=None,subject=None,confidence=.5,source_journal_id=None,outcome='unresolved'):
    await ensure_schema()
    async with connection() as c:
        return await c.fetchval('''INSERT INTO colony_mind_memory(run_id,kind,subject,lesson,evidence,confidence,source_journal_id,outcome)
          VALUES($1,$2,$3,$4,$5::jsonb,$6,$7,$8) RETURNING id''',run_id,kind,subject,lesson,json.dumps(evidence or {}),confidence,source_journal_id,outcome)

async def recall(run_id,limit=8):
    await ensure_schema()
    async with connection() as c:
        rows=await c.fetch('''SELECT kind,subject,lesson,confidence,outcome,created_at FROM colony_mind_memory
          WHERE run_id=$1 ORDER BY (outcome<>'unresolved') DESC, confidence DESC, created_at DESC LIMIT $2''',run_id,limit)
    return [dict(r) for r in rows]

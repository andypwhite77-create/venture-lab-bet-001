"""Durable admission registry for independent prospective research probation.
This registry never pretends registration is proof that a strategy was replayed.
"""
import json
SCHEMA='''CREATE TABLE IF NOT EXISTS finalist_probation(
 genome_id text NOT NULL, campaign integer NOT NULL, admitted_at timestamptz NOT NULL DEFAULT now(),
 status text NOT NULL DEFAULT 'awaiting_prospective_engine', genome jsonb,
 family text NOT NULL DEFAULT 'queen_pattern',
 PRIMARY KEY(genome_id,campaign));'''
async def ensure_schema(conn):
 await conn.execute(SCHEMA)

async def admit(conn,campaign,finalists,spartan_results):
 await ensure_schema(conn)
 passed={r.get('genome_id') for r in spartan_results if r.get('qualification_pass') and r.get('genome_id')}
 admitted=0
 for f in finalists:
  gid=f.get('genome_id')
  if gid not in passed:continue
  result=await conn.execute('''INSERT INTO finalist_probation(genome_id,campaign,genome)
     VALUES($1,$2,$3::jsonb) ON CONFLICT DO NOTHING''',gid,int(campaign),json.dumps(f.get('genome') or {}))
  admitted+=int(result.endswith('1'))
 return {'new_probation_records':admitted,'status':'awaiting_prospective_engine','authority':'research_only_no_automatic_trading'}

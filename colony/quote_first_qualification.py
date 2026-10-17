"""Conservative research qualification from candidate-time Jupiter evidence.
A route quote is not a transaction, execution, or proof of profitability.
"""
import asyncio,json
from db import init_db,connection
SCHEMA='''CREATE TABLE IF NOT EXISTS quote_first_qualification_reviews(id bigserial PRIMARY KEY, reviewed_at timestamptz NOT NULL DEFAULT now(), report jsonb NOT NULL);'''
def classify(row):
 if row['quote_status']!='quoted' or not row['quote']:return 'no_contemporaneous_quote'
 if row['latency_seconds'] is None or float(row['latency_seconds'])<0 or float(row['latency_seconds'])>10:return 'late_or_invalid_quote'
 q=row['quote']
 if isinstance(q,str):
  try:q=json.loads(q)
  except (TypeError,ValueError):return 'malformed_quote'
 try:
  if int(q['in_amount'])<=0 or int(q['out_amount'])<=0 or not q.get('route_labels'):return 'incomplete_route'
 except (KeyError,TypeError,ValueError):return 'incomplete_route'
 return 'prospective_route_evidence_only'
def assess(rows):
 counts={}
 for r in rows:
  label=classify(r);counts[label]=counts.get(label,0)+1
 return {'total':len(rows),'classifications':counts,'policy':'Only prospective sized quotes count as route evidence; no quote is a fill and no reference-price paper return is qualifying PnL.','authority':'audit_only_no_live'}
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  rows=await c.fetch('''SELECT r.id,q.status quote_status,q.quote,q.latency_seconds FROM research_candidates r LEFT JOIN research_candidate_birth_quotes q ON q.candidate_id=r.id WHERE r.created_at>now()-interval '24 hours' ORDER BY r.id''')
  result=assess([dict(r) for r in rows])
  await c.execute('INSERT INTO quote_first_qualification_reviews(report) VALUES($1::jsonb)',json.dumps(result))
 return result
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

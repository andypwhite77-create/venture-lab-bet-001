"""Read-only diagnosis of funded hypothetical reservations without verified releases."""
import asyncio,json
from collections import Counter
from db import init_db,connection

def classify(reason):
 text=str(reason or '')
 if 'missing_contemporaneous_entry_quote' in text:return 'entry_quote_context_missing'
 if '429' in text or 'cooldown' in text:return 'provider_rate_limit'
 if 'no_route' in text:return 'route_unavailable'
 return 'unclassified_exit_evidence_gap'
async def run():
 await init_db()
 async with connection() as c:
  rows=await c.fetch('''SELECT d.genome_id,d.source_entry_id,e.family,x.status exit_status,x.reason exit_reason
  FROM funded_paper_event_decisions d JOIN eve_reference_paper_entries e ON e.id=d.source_entry_id
  LEFT JOIN canary_forward_quote_observations x ON x.entry_id=e.id AND x.phase='exit'
  WHERE d.action='reserve' AND d.accepted AND NOT EXISTS
  (SELECT 1 FROM funded_paper_event_decisions r WHERE r.genome_id=d.genome_id AND r.source_entry_id=d.source_entry_id AND r.action='release' AND r.accepted)
  ORDER BY d.genome_id,d.source_entry_id''')
 by_family={}
 for r in rows:
  f=r['family'];entry=by_family.setdefault(f,{'unresolved':0,'causes':Counter()})
  entry['unresolved']+=1;entry['causes'][classify(r['exit_reason'])]+=1
 return {'families':{k:{'unresolved':v['unresolved'],'causes':dict(v['causes'])} for k,v in by_family.items()},'authority':'read_only_no_synthetic_releases','note':'Missing quote evidence must not be booked as an economic exit or filled price.'}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

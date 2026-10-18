"""Fail-closed hypothetical funded-ledger family attribution using independently stored provenance."""
import asyncio,json
from collections import defaultdict
from datetime import datetime,timezone
from db import init_db,connection
from colony.capital_efficiency_scoreboard import score

def audit(events,genomes,as_of,cohorts=(),entries=()):
 registry=defaultdict(set);cohort=defaultdict(set);entry=defaultdict(set)
 for x in genomes:registry[str(x['genome_id'])].add(str(x['family']))
 for x in cohorts:cohort[str(x['genome_id'])].add(str(x['family']))
 for x in entries:entry[str(x['genome_id'])].add(str(x['family']))
 funded=score(events,as_of) if events else {}
 families={};unmapped=[]
 for gid,metrics in sorted(funded.items()):
  first=cohort.get(gid,set());second=entry.get(gid,set());third=registry.get(gid,set())
  # Require two matching sources. A contradictory main registry is disqualifying.
  verified=len(first)==len(second)==1 and first==second and (not third or third==first)
  if not verified:
   unmapped.append({'genome_id':gid,'cohort_families':sorted(first),'entry_families':sorted(second),'registry_families':sorted(third),'reason':'provenance_missing_or_conflicting'});continue
  family=next(iter(first))
  families.setdefault(family,[]).append({'genome_id':gid,**metrics})
 return {'families':families,'unmapped_genomes':unmapped,'matched_genomes':sum(len(v) for v in families.values()),'unmapped_count':len(unmapped),'economic_rewards':None,'authority':'quote_derived_hypothetical_audit_only','warning':'Two-source family labels, not trade fills or promotion proof.'}
async def run():
 await init_db()
 async with connection() as c:
  events=await c.fetch('SELECT source_event_id,genome_id,source_entry_id,action,amount_lamports,accepted,decided_at FROM funded_paper_event_decisions ORDER BY source_event_id')
  genomes=await c.fetch('SELECT genome_id,family FROM colony_genomes')
  cohorts=await c.fetch('SELECT genome_id,family FROM controlled_paper_cohort')
  entries=await c.fetch('SELECT DISTINCT genome_id,family FROM eve_reference_paper_entries')
 return audit(events,genomes,datetime.now(timezone.utc),cohorts,entries)
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

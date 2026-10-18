"""Audited, fail-closed family attribution for hypothetical funded cash events.
Unmatched genome IDs remain unassigned. No economic rewards or live authority.
"""
import asyncio,json
from datetime import datetime,timezone
from db import init_db,connection
from colony.capital_efficiency_scoreboard import score

def audit(events,genomes,as_of):
 mapping={}
 for item in genomes:
  g=dict(item);gid=str(g['genome_id']);family=str(g['family'])
  if gid in mapping and mapping[gid]!=family:mapping[gid]=None
  elif gid not in mapping:mapping[gid]=family
 allowed={'reversal','momentum','exhaustion','pattern_recognition'}
 groups=score(events,as_of) if events else {}
 attributed={};unmapped=[]
 for gid,m in sorted(groups.items()):
  family=mapping.get(gid)
  if family not in allowed:unmapped.append({'genome_id':gid,'reason':'missing_or_ambiguous_family','completed':m['completed_quote_round_trips']});continue
  attributed.setdefault(family,[]).append({'genome_id':gid,**m})
 return {'families':attributed,'unmapped_genomes':unmapped,'matched_genomes':sum(map(len,attributed.values())),'unmapped_count':len(unmapped),'economic_rewards':None,'authority':'quote_derived_hypothetical_audit_only','warning':'Unmapped funds excluded; accepted events are not executable fills.'}
async def run():
 await init_db()
 async with connection() as c:
  events=await c.fetch('SELECT source_event_id,genome_id,source_entry_id,action,amount_lamports,accepted,decided_at FROM funded_paper_event_decisions ORDER BY source_event_id')
  genomes=await c.fetch('SELECT genome_id,family FROM colony_genomes')
 return audit(events,genomes,datetime.now(timezone.utc))
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

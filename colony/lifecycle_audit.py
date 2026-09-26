"""Audit that evolutionary evidence is matured and temporally valid."""
from db import connection
RUN='fwd-g3-20260926T084022Z'
async def audit(run_id=RUN):
 async with connection() as c:
  r=await c.fetchrow("""SELECT count(*) entries,
   count(*) FILTER (WHERE EXISTS(SELECT 1 FROM research_outcomes o WHERE o.candidate_id=e.candidate_id AND o.measured_at>=e.observed_at)) matured,
   count(*) FILTER (WHERE EXISTS(SELECT 1 FROM research_outcomes o WHERE o.candidate_id=e.candidate_id AND o.measured_at<e.observed_at)) pre_entry_outcomes
   FROM colony_forward_entries e WHERE e.run_id=$1""",run_id)
  unresolved=await c.fetchval("""SELECT count(*) FROM colony_forward_entries e WHERE e.run_id=$1 AND NOT EXISTS
   (SELECT 1 FROM research_outcomes o WHERE o.candidate_id=e.candidate_id AND o.measured_at>=e.observed_at)""",run_id)
 return {**dict(r),'unresolved':unresolved,'selection_must_use_matured_only':True}

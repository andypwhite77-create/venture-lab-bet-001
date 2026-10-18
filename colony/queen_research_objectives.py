"""Verified paper-economics diagnostics for bounded Queen research prompts."""
from datetime import datetime,timezone
from db import connection
from colony.queen_funded_attribution import audit
from colony.queen_economic_feedback import explain

async def family_objective(queen):
 async with connection() as c:
  events=await c.fetch('SELECT source_event_id,genome_id,source_entry_id,action,amount_lamports,accepted,decided_at FROM funded_paper_event_decisions ORDER BY source_event_id')
  genomes=await c.fetch('SELECT genome_id,family FROM colony_genomes')
  cohorts=await c.fetch('SELECT genome_id,family FROM controlled_paper_cohort')
  entries=await c.fetch('SELECT DISTINCT genome_id,family FROM eve_reference_paper_entries')
 result=explain(audit(events,genomes,datetime.now(timezone.utc),cohorts,entries))
 data=result['families'].get(queen)
 return {'family':queen,'feedback':data,'evidence':'attributed_hypothetical_quotes_not_fills','allowed_action':'research_hypothesis_only'}

def objective_prompt(data):
 feedback=data.get('feedback')
 if not feedback:return 'No attributed funded-paper feedback available. Propose a falsifiable entry hypothesis; do not infer profitability.'
 tags=feedback.get('research_priorities',[])
 return ('Economic diagnostic priorities: '+', '.join(tags or ['collect_independent_forward_evidence'])+'. '
  'Hypothetical net SOL: '+str(feedback['hypothetical_net_sol'])+'. Pending: '+str(feedback['pending'])+'. '
  'Choose a falsifiable entry hypothesis plausibly related to one priority; do not claim an entry filter can repair execution or locked capital. '
  'These are symptoms from quote evidence, NOT proven causes or real earnings.')

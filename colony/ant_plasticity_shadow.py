"""Shadow lifetime plasticity: frozen DNA, reversible adaptive selectivity.
No order placement, changes to reference entries, breeding, or promotions.
Decisions use only marks observed before each entry timestamp.
"""
import asyncio,json
from db import init_db,connection

SCHEMA="""CREATE TABLE IF NOT EXISTS ant_plasticity_shadow_runs(
 id bigserial primary key, created_at timestamptz not null default now(),
 report jsonb not null, authority text not null default 'shadow_no_live_authority');"""

def evaluate(entries, marks, window=8, min_history=4, cooldown_losses=3):
    """Ordered, causal paper-only decisions; abstentions don't rewrite frozen entries."""
    by_ant={}; output=[]
    # only marks with outcome timestamps strictly preceding signal may influence it
    for e in sorted(entries,key=lambda x:(x['observed_at'],x['entry_id'])):
        aid=e['genome_id']; t=e['observed_at']; history=by_ant.setdefault(aid,[])
        eligible=[m for m in marks.get(aid,[]) if m['outcome_at']<t]
        recent=sorted(eligible,key=lambda m:(m['outcome_at'],m['entry_id']))[-window:]
        mean=sum(m['net_pct'] for m in recent)/len(recent) if recent else None
        losing_streak=0
        for m in reversed(recent):
            if m['net_pct']<0:losing_streak+=1
            else:break
        # A fixed rule; no optimising thresholds against the same outcomes.
        abstain=len(recent)>=min_history and (losing_streak>=cooldown_losses or (mean is not None and mean < -5))
        output.append({'entry_id':e['entry_id'],'genome_id':aid,'observed_at':t,
                       'shadow_action':'abstain' if abstain else 'follow_dna',
                       'known_marks':len(recent),'recent_mean':round(mean,3) if mean is not None else None,
                       'loss_streak':losing_streak})
    return output

async def run():
    await init_db()
    async with connection() as c:
        await c.execute(SCHEMA)
        entries=await c.fetch("""SELECT e.id entry_id,e.genome_id,e.observed_at
          FROM eve_reference_paper_entries e JOIN controlled_paper_cohort cohort
          ON e.genome_id=cohort.genome_id AND e.observed_at>=cohort.started_at
          WHERE cohort.status='observation_only' ORDER BY e.observed_at,e.id""")
        ledger=await c.fetch("""SELECT l.entry_id,l.genome_id,l.outcome_at,
           l.net_return_pct net_pct FROM controlled_paper_trade_ledger l
           JOIN controlled_paper_cohort c ON l.genome_id=c.genome_id
           WHERE c.status='observation_only' ORDER BY l.outcome_at,l.entry_id""")
        by={}; returns={}
        for m in ledger:
            by.setdefault(m['genome_id'],[]).append(dict(m));returns[m['entry_id']]=float(m['net_pct'])
        choices=evaluate([dict(x) for x in entries],by)
        selected=[x for x in choices if x['shadow_action']=='follow_dna']
        completed=[x for x in selected if x['entry_id'] in returns]
        baseline=[returns[x['entry_id']] for x in choices if x['entry_id'] in returns]
        shadow=[returns[x['entry_id']] for x in completed]
        report={'version':'plasticity_shadow_v1','entries':len(choices),'follow_dna':len(selected),
          'abstentions':len(choices)-len(selected),'marked_baseline_count':len(baseline),
          'marked_shadow_count':len(shadow),'baseline_nominal_sum_pct':round(sum(baseline),3),
          'shadow_nominal_sum_pct':round(sum(shadow),3),
          'baseline_worst_pct':min(baseline) if baseline else None,
          'shadow_worst_pct':min(shadow) if shadow else None,
          'authority':'advisory_only_no_genome_changes_no_breeding_no_live',
          'caveats':['Outcome timestamps gate experience; marks may still be biased or revised.',
          'Skipped signals are zero exposure, not substitute winning trades.',
          'Nominal sums ignore overlapping positions, capital usage and execution costs beyond ledger assumptions.',
          'Rule is fixed and must pass a fresh prospective cohort before qualification.']}
        rid=await c.fetchval('INSERT INTO ant_plasticity_shadow_runs(report) VALUES($1::jsonb) RETURNING id',json.dumps(report))
        return {'id':rid,**report}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

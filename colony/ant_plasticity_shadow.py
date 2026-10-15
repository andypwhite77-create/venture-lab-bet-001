"""Shadow lifetime plasticity: frozen DNA, reversible adaptive selectivity.
No order placement, changes to reference entries, breeding, or promotions.
Decisions use only marks observed before each entry timestamp.
"""
import asyncio,json,math
from datetime import timezone
from db import init_db,connection

SCHEMA="""CREATE TABLE IF NOT EXISTS ant_plasticity_shadow_runs(
 id bigserial primary key, created_at timestamptz not null default now(),
 report jsonb not null, authority text not null default 'shadow_no_live_authority');"""

def regime(features):
    """Classify only entry-time indicators; missing signals remain unknown."""
    f=json.loads(features) if isinstance(features,str) else (features or {})
    def number(key):
        try:
            v=float(f[key]);return v if math.isfinite(v) else None
        except (KeyError,TypeError,ValueError):return None
    liquidity=number('liquidity_usd');change=number('price_change_m5')
    if liquidity is not None and liquidity<25000:return 'thin_liquidity'
    if change is not None and abs(change)>=15:return 'high_momentum_volatility'
    if liquidity is None or change is None:return 'unknown'
    return 'ordinary'

def evaluate(entries, marks, window=8, min_history=4, cooldown_losses=3, half_life_hours=24):
    """Causal, reversible decisions from settled history; never uses current outcome."""
    output=[]
    for e in sorted(entries,key=lambda x:(x['observed_at'],x['entry_id'])):
        aid=e['genome_id'];t=e['observed_at']; band=regime(e.get('features'))
        eligible=[m for m in marks.get(aid,[]) if m['outcome_at']<t]
        recent=sorted(eligible,key=lambda m:(m['outcome_at'],m['entry_id']))[-window:]
        weighted=[]
        for m in recent:
            age=max(0,(t-m['outcome_at']).total_seconds()/3600)
            weighted.append((float(m['net_pct']),2**(-age/half_life_hours)))
        mean=sum(v*w for v,w in weighted)/sum(w for _,w in weighted) if weighted else None
        losing_streak=0
        for m in reversed(recent):
            if m['net_pct']<0:losing_streak+=1
            else:break
        # Stale outcomes lose decision authority even if their signed mean remains negative.
        effective_marks=sum(w for _,w in weighted)
        enough=len(recent)>=min_history and effective_marks>=1.5
        regime_caution=band=='thin_liquidity' and enough and mean is not None and mean<0
        abstain=enough and (losing_streak>=cooldown_losses or (mean is not None and mean < -5) or regime_caution)
        output.append({'entry_id':e['entry_id'],'genome_id':aid,'observed_at':t,
                       'shadow_action':'abstain' if abstain else 'follow_dna','regime':band,
                       'known_marks':len(recent),'effective_marks':round(effective_marks,3),'recent_mean':round(mean,3) if mean is not None else None,
                       'loss_streak':losing_streak})
    return output

async def run():
    await init_db()
    async with connection() as c:
        await c.execute(SCHEMA)
        entries=await c.fetch("""SELECT e.id entry_id,e.genome_id,e.observed_at,r.features
          FROM eve_reference_paper_entries e JOIN research_candidates r ON r.id=e.candidate_id JOIN controlled_paper_cohort cohort
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
        missed=[returns[x['entry_id']] for x in choices if x['shadow_action']=='abstain' and x['entry_id'] in returns]
        regimes={}
        for choice in choices:
            z=regimes.setdefault(choice['regime'],{'signals':0,'abstentions':0})
            z['signals']+=1;z['abstentions']+=int(choice['shadow_action']=='abstain')
        report={'version':'plasticity_shadow_v2','entries':len(choices),'follow_dna':len(selected),
          'abstentions':len(choices)-len(selected),'marked_baseline_count':len(baseline),
          'marked_shadow_count':len(shadow),'baseline_nominal_sum_pct':round(sum(baseline),3),
          'shadow_nominal_sum_pct':round(sum(shadow),3),
          'missed_marked_count':len(missed),'missed_winners':sum(x>0 for x in missed),
          'missed_losers':sum(x<0 for x in missed),'missed_nominal_sum_pct':round(sum(missed),3),
          'by_entry_regime':regimes,'memory_half_life_hours':24,
          'baseline_worst_pct':min(baseline) if baseline else None,
          'shadow_worst_pct':min(shadow) if shadow else None,
          'authority':'advisory_only_no_genome_changes_no_breeding_no_live',
          'caveats':['Outcome timestamps gate experience; marks may still be biased or revised.',
          'Skipped signals are zero exposure, not substitute winning trades.',
          'Nominal sums ignore overlapping positions, capital usage and execution costs beyond ledger assumptions.',
          'The rule was designed after inspecting earlier data; this is not an out-of-sample performance claim.',
          'Rule is fixed and must pass a fresh prospective cohort before qualification.']}
        rid=await c.fetchval('INSERT INTO ant_plasticity_shadow_runs(report) VALUES($1::jsonb) RETURNING id',json.dumps(report))
        return {'id':rid,**report}
if __name__=='__main__':print(json.dumps(asyncio.run(run())))

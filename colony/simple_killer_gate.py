"""Simple, conservative paired benchmark for historical hypothesis screening.

Never a promotion gate: a reused research holdout cannot establish prospective edge.
"""
import math
import statistics


def assess(selected, baseline, distinct_mints, minimum=25, friction_stress_pct=1.5):
    """Returns read-only diagnosis for the same chronological market partition.

    baseline is the unfiltered opportunity set for the identical partition.
    Missing values fail closed; no invented losses or fills.
    """
    s=list(selected); b=list(baseline)
    if len(s)<minimum or len(b)<minimum or distinct_mints<minimum:
        return {'passes_screen':False,'reason':'insufficient_independent_opportunities','n':len(s),'distinct_mints':distinct_mints}
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in s+b):
        return {'passes_screen':False,'reason':'invalid_return'}
    stress=[x-friction_stress_pct for x in s]
    ordered=sorted(stress)
    tail=ordered[:max(1,math.ceil(len(ordered)*.1))]
    mean=statistics.fmean(stress)
    median=statistics.median(stress)
    base=statistics.fmean(b)
    tail_mean=statistics.fmean(tail)
    # Earn positive economics AND improve on the simple buy-all baseline.
    passed=mean>0 and median>0 and mean>base and tail_mean>=-15
    return {'passes_screen':passed,'reason':'screen_passed_research_only' if passed else 'no_robust_economic_advantage',
            'n':len(s),'distinct_mints':distinct_mints,
            'stressed_mean_pct':round(mean,4),'stressed_median_pct':round(median,4),
            'baseline_mean_pct':round(base,4),'worst_decile_mean_pct':round(tail_mean,4),
            'additional_stress_pct_points':friction_stress_pct,
            'promotion_allowed':False}

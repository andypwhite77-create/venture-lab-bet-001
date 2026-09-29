"""Spartan v2 adversarial qualification layer.
Research/paper only. Adds path survival, friction perturbation, opportunity efficiency,
and behavioural diversity to the existing chronological evidence pipeline.
"""
from dataclasses import dataclass
import math,random,statistics

@dataclass
class StressResult:
    mean_net: float
    p05_net: float
    cvar_10: float
    survival_rate: float
    max_drawdown: float
    friction_break_even: float


def max_drawdown(returns):
    equity=peak=1.0; worst=0.0
    for r in returns:
        equity*=max(0.0,1.0+r)
        peak=max(peak,equity)
        worst=max(worst,(peak-equity)/peak if peak else 1.0)
    return worst


def cvar(values,q=.10):
    if not values:return -1.0
    s=sorted(values); n=max(1,math.ceil(len(s)*q))
    return sum(s[:n])/n
def stress_returns(raw_returns, base_friction, trials=500, seed='spartan-v2'):
    """Monte Carlo execution torture. raw_returns are pre-friction decimal returns."""
    rng=random.Random(seed); paths=[]; dds=[]
    multipliers=(1.0,1.0,1.0,1.5,1.5,2.0,2.0,3.0)
    for _ in range(trials):
        path=[]
        for r in raw_returns:
            mult=rng.choice(multipliers)
            latency_drag=max(0.0,rng.gauss(base_friction*.25,base_friction*.20))
            slippage=max(0.0,rng.gauss(base_friction*.20,base_friction*.20))
            path.append(r-(base_friction*mult)-latency_drag-slippage)
        paths.append(sum(path)); dds.append(max_drawdown(path))
    ordered=sorted(paths)
    return StressResult(statistics.mean(paths),ordered[max(0,int(.05*len(ordered))-1)],
        cvar(paths,.10),sum(d<=.15 for d in dds)/len(dds),max(dds),
        min((m for m in (1,1.5,2,2.5,3) if sum(r-base_friction*m for r in raw_returns)<=0),default=3.5))


def opportunity_efficiency(taken_returns,rejected_returns):
    """Reward selective participation, never abstention by itself."""
    captured=sum(max(0,r) for r in taken_returns)
    missed=sum(max(0,r) for r in rejected_returns)
    avoided=sum(max(0,-r) for r in rejected_returns)
    bad_taken=sum(max(0,-r) for r in taken_returns)
    denom=captured+missed+avoided+bad_taken
    return (captured+avoided)/denom if denom else 0.0
def behavioural_distance(events_a,events_b):
    """Jaccard distance: genetic diversity does not count if ants take same opportunities."""
    a,b=set(events_a),set(events_b)
    if not a and not b:return 0.0
    return 1.0-(len(a&b)/len(a|b))


def qualifies(stress, expectancy, opp_eff, winner_concentration,
              min_expectancy=0.0,min_survival=.95,min_opp_eff=.55,max_concentration=.55):
    return (expectancy>min_expectancy and stress.mean_net>0 and stress.p05_net>0
            and stress.cvar_10>0 and stress.survival_rate>=min_survival
            and opp_eff>=min_opp_eff and winner_concentration<=max_concentration)

# Policy: discovery -> chronological validation -> untouched holdout -> Spartan v2
# torture -> behavioural diversity -> prospective paper. Historical success never
# grants live-money authority. Mirror/inversion is diagnostic, not a universal gate.

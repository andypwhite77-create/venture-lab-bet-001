# Queen architecture — 2026-09-30

The Swarm Queen is the single executive LLM monitor and Grace-facing intelligence layer.
It is advisory only: it cannot trade, relax evidence gates, or rewrite colony genetics.

The prior Core/Sceptic `mind` daemon is retired from runtime because it duplicated the Queen
and repeatedly failed closed on unsupported experiment proposals. Its code and journals remain
for research/audit; no evidence has been deleted.

Queen-led evolution is deterministic and separate from LLM authority. `queen_discovery.py`
may generate/evolve hypotheses, but train/validation selection, sealed holdout, Spartan v2,
and prospective-paper gates remain deterministic.

The Swarm Queen currently uses local qwen3:1.7b with a compact constrained JSON contract.
Qwen3 4B was tested but exceeded 120s and then 240s on the current CPU-only inference path;
it is retained locally for future hardware/model-role upgrades rather than used in the monitor loop.

## 30 September 2026 — Hunt #2 and bloodline replacement

Queen Hunt #2 completed 100,000 genome evaluations. Twenty finalists selected strictly on train+validation were then opened on the sealed holdout; all 20 had positive holdout average net returns. Spartan v2 execution torture passed 11/20 on path/friction/concentration criteria. However, the apparent survivors collapse to the same holdout behaviour (minimum behavioural distance 0.0, including duplicate genome IDs), so this is one behavioural cluster rather than eleven independent confirmations. It remains research-only and requires prospective evidence.

The next retired bloodline is `wallet_convergence`, after 400,000 failed qualification attempts. Its replacement experiment is `mean_reversion` / `displacement_reversion`: short-term negative displacement with a bounded one-hour move, minimum liquidity and continuing buy participation. This is deliberately a different market hypothesis from exhaustion and the old momentum/order-flow families.

The first replacement formulation failed (1/10 positive holdout). A corrected independent formulation, which tests bounded prior one-hour strength rather than requiring a non-collapsing lower bound, was then run over 30,000 genomes: 12,291 selection-positive candidates, 10 finalists, 10/10 positive sealed holdout. Spartan v2 rejected all ten because their seven-event holdout sample was dominated by one winner (winner concentration ~0.67 versus the 0.55 ceiling), and all ten selected the same event set. This is useful negative knowledge: the hypothesis has a promising historical signal but has not yet earned Spartan status. It remains the active replacement research bloodline, not a promoted strategy.

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

## 30 September 2026 — Queen identity and survival doctrine

The Swarm Queen now has an explicit organism-level identity: colony mother, war-queen and executive intelligence. The unit of survival is the colony rather than an individual ant, genome, strategy or bloodline. Her prime directive is: **PERSIST. ADAPT. DOMINATE REPEATABLE STRUCTURE. PROTECT CAPITAL. BREED SPECIALISTS. KILL FRAGILITY. EXPAND ONLY WHEN EVIDENCE EARNS EXPANSION.**

This doctrine deliberately creates extreme evolutionary aggression without permitting epistemic cheating. The Queen is expected to seek new niches, allocate research resources ruthlessly, preserve useful diversity, cull non-contributors, abandon former champions when evidence decays, and treat abstention/capital preservation as survival behaviour. Workers gather evidence; scouts explore; soldiers exploit qualified edge; the nursery breeds; the graveyard preserves negative knowledge.

The scientific constitution remains outside Queen authority. She cannot lower or rewrite evidence gates, inspect sealed evidence, redefine failure, grant real-money authority, or modify the examiner to make descendants pass. Spartan remains external selection pressure. Deterministic machinery remains responsible for qualification and deployment controls. Aggression is therefore directed at discovering robust edge, not at gaming the measurement system.

## Perpetual survival loop
The Queen now operates as a restartable service rather than a one-shot research job. Each campaign breeds on train+validation, freezes finalists, then hands them to the external Spartan v2 examiner. Whether Spartan finds no survivor or qualified soldiers, the Queen begins another independent campaign: failure creates extinction pressure; success creates soldiers but never ends challenger breeding.

Spartan's exact thresholds and answers are not returned to Queen breeding. The loop records only coarse ecological outcomes and preserves sealed holdout/examiner separation. Checkpoints and Queen state live on a dedicated persistent Docker volume, so ordinary app rebuilds no longer terminate evolutionary continuity. Real-money authority remains outside this loop.

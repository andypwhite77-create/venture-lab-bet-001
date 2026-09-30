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

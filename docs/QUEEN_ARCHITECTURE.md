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

## Cross-campaign expertise memory
Queen now retains breeding-visible research knowledge across campaigns instead of resetting to a near-blank search. Finalists contribute feature-use and training/validation fitness evidence to a persistent Queen memory. That memory biases subsequent scout generation toward repeatedly useful sensors while preserving 20% fresh exploration and ordinary mutation, preventing the memory from collapsing the search into one inherited local optimum.

Memory never contains Spartan thresholds, Spartan failure details, or sealed holdout outcomes. The Queen can therefore become better at choosing where to search without learning the examiner. Each campaign records accumulated experience and preferred research features; the survival loop continues whether soldiers are found or exterminated. This is the first layer of a longer-term world model rather than a claim that the Queen is autonomous or conscious.

## Expertise ecology: journal, graveyard, niches, aging and controls
Queen now maintains a persistent breeding-visible research ecology. Each completed campaign journals its scale and niche count; finalists are clustered by behavioural feature/holding-horizon signature so differently written genomes do not automatically masquerade as independent ideas. Repeated weak niches enter a reversible graveyard rather than being forgotten. Belief confidence decays by 8% per campaign unless refreshed by new breeding-visible evidence, preventing old discoveries from becoming permanent folklore.

Queen also maintains an opportunity map of underexplored sensors and a meta-allocation doctrine: approximately 55% exploitation of accumulated useful territory, 25% adjacent exploration and 20% wild scouting. The existing fresh-blood mechanism remains the hard diversity floor. This strategy state is advisory to breeding and cannot alter evidence gates or deployment authority.

A newborn/shadow-Queen control is defined but intentionally not allowed to reuse the current sealed evidence. It will be run periodically only when a retired-evidence split can be isolated cleanly; this prevents the control itself from leaking the examiner into breeding. The purpose is to test whether accumulated Queen expertise beats a memoryless researcher, rather than assuming that memory is useful.

The dashboard/command layer should surface Queen beliefs, top niches, graveyard size, underexplored territory and changing confidence. These are auditable research beliefs, not claims of consciousness or guaranteed market edge.

## Queen resource uplift after Spartan hardening
Spartan's examiner remains sealed, but Queen has been given more breeding-visible resources rather than being weakened. Selection now rewards broader train/validation participation and specifically rewards validation coverage that does not collapse relative to training. Minimum breeding evidence rises to 18 train and 12 validation events. Parent selection also caps repeated train/validation phenotypes so one narrow behavioural niche cannot monopolise the 300-parent breeding pool.

This is deliberately asymmetric: Queen receives better search pressure, diversity and generalisation resources, while Spartan's isolated holdout, 25-opportunity floor and behavioural deduplication remain untouched. The objective is to breed genuinely stronger organisms, not lower the exam standard.

## Queen sensory expansion — 2026-09-30
Queen's breeding vocabulary now includes derived, present-time context sensors computed only from information available at the observation: trend alignment, short-vs-hour movement, 15/30-window flow imbalance, flow shift, and 30-window activity. These features are available equally to train, validation and sealed holdout evaluation; future returns are never used to construct them.

Genomes may also evolve hold horizon plus conservative stop-loss and take-profit parameters. Because the archive currently stores horizon outcomes rather than full intrahorizon price paths, risk management is scored conservatively: a stop or target is credited only when the observed horizon endpoint itself crosses that level. This avoids inventing fills from price paths we do not possess. Path-aware exits remain a future upgrade once candle/trade-path history is available.

This expansion deliberately gives Queen more expressive organisms without weakening Spartan or revealing holdout information. Existing campaigns/checkpoints remain historical evidence; new sensory vocabulary takes effect only in newly bred populations after deployment.

## Queen lifecycle/context sensor package — 2026-09-30
Queen can now evolve against the remaining useful context already present in the archive: pair age, hourly activity, hourly buy/sell imbalance, recent buy-activity change, hourly volume relative to liquidity, FDV/liquidity and market-cap/liquidity. These are derived only from information available at the observation timestamp and are exposed consistently across train, validation and sealed holdout.

This package does not add new market data; it exposes more of the data we already collect. The main remaining bottleneck is now dataset breadth and age rather than unused archived fields.

## Specialist council + historical context — 2026-09-30
Queen now receives a council layer without merging specialist genetics. Reversal, Momentum, Order Flow, Exhaustion and Mean Reversion expose fixed archetype signals derived only from observation-time market features. Actual prospective tournament firings are also attached by candidate ID, so Queen may learn when independent specialist ants agreed or disagreed without back-projecting today's evolved winners into earlier history.

The local GeckoTerminal historical bank is now used as past-only context. For candidate observations whose pool has archived hourly bars, Queen receives trailing 24h/7d return, 24h volatility, recent/prior volume ratio, seven-day drawdown and seven-day price position. Every historical feature is computed using bars timestamped at or before the candidate observation; future bars, candidate outcomes and Spartan evidence are excluded.

This is a hierarchical design: specialist ants remain free to trade/paper-trade their own niches, while the general Queen may evolve rules using raw sensors, specialist opinions, actual prospective specialist firings and historical regime context. Queen's persistent cross-campaign memory remains the single breeding memory. Spartan remains external and sealed.


## 1 October 2026 — three-layer Queen hierarchy and career inheritance

Runtime is now conceptually reduced to three organism layers: **Swarm Queen → Breeding Queen → ants**. The Swarm Queen is the read-only executive/Grace-facing synthesis layer. The Breeding Queen is the deterministic evolutionary organism tested by external Spartan. All named strategies (Reversal, Exhaustion, Mean Reversion and future niches) are ant colonies rather than separate Queens. The retired Core/Sceptic `mind` service remains in source history but is placed behind the `legacy` Compose profile so ordinary deployment cannot accidentally reactivate it.

Prospective ant careers now feed the Breeding Queen. Deployed ants remain immutable: no ant rewrites itself while being measured. Instead, completed prospective tournament outcomes are compressed into career statistics, successful predicate families and a small set of experienced parent templates. The Breeding Queen may allocate up to 20% of a new first-wave population to mutated descendants of those experienced templates; the rest remains normal memory-guided/wild exploration. Poor careers contribute negative evidence and do not become parent templates.

To preserve the exam, every mint whose prospective outcome contributed to career learning is quarantined from the Breeding Queen's historical train/validation/holdout dataset. Thus career experience can influence descendants without leaking an outcome back into Spartan's sealed historical evidence. Spartan thresholds and logic remain unchanged. The resulting lifecycle is: **frozen ant trades → career evidence accumulates → Breeding Queen learns → descendants are born → descendants face ordinary evidence gates → Spartan remains external examiner**.

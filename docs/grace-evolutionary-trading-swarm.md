# Grace Evolutionary Trading Swarm

Status: implemented prospective paper experiment
Updated: 2026-09-28

## Core idea

Build a market research organism rather than one giant AI trader. A central sensing layer observes the market; many simple structured genomes (“ants”) interpret that shared environment; strategy families compete; a small Core/Queen proposes experiments; a separate Sceptic attacks them; deterministic software controls validation, risk, execution and authority.

The long-run objective is a research factory that discovers, tests, kills and reproduces small positive-expectancy behaviours without requiring a human to hand-design the eventual winning strategy.

## What is now running

The prototype has moved beyond the original concept note. It now runs continuously on a VPS with PostgreSQL and Docker Compose. A persistent paper daemon survives restarts. The forward population contains momentum, reversal and wallet-convergence families and has been around 89 distinct genomes during the initial run.

The colony can originate its own prospective paper intents. Each intent records candidate, family, exact contributing genome IDs and consensus count, requests an executable Jupiter quote, passes through deterministic risk limits, enters an execution ledger with `broadcast=false`, and is subsequently marked using later independent market prices.

This is deliberately separate from the older external wallet-convergence signal stream. Historical external signals are not falsely labelled as having been authored by an ant.

## Current paper-risk envelope

The initial colony-native run uses:

- 0.005 SOL nominal paper position size;
- 0.1 SOL aggregate simulated exposure ceiling;
- no real transaction broadcasting;
- modelled execution friction;
- executable quote capture before acceptance;
- deterministic duplicate/exposure protection.

The risk gate has already demonstrated a refusal when aggregate exposure reached its ceiling. The colony cannot increase its own allocation.

The 0.1 SOL ceiling is an exposure allowance, not yet a complete cash-account bankroll. Until proper account accounting is implemented, performance should be described as P&L generated under that exposure envelope rather than a rigorous return on a £9 account.

## Performance telemetry

A live read-only dashboard is available at `https://colony.cobaltindustrial.tech/dashboard`. It displays colony-native bets, number marked, win rate, cumulative net P&L, SOL-to-GBP equivalent, ant population, real transaction count, equity/P&L curve, bloodline results, attributed trades and Queen/Sceptic state. Bloodline net values are displayed in both SOL and GBP.

“Marked” means a paper bet has been repriced against a later live market price and therefore has a measurable mark-to-market P&L. It does not yet mean a strategy-defined exit has closed the position. Future versions should explicitly separate OPEN, MARKED/MTM and CLOSED.

The dashboard is intentionally observational. The public gateway does not expose signing or trading-control endpoints.

## Economic objective

The eventual experiment is whether tiny external capital can grow without repeated owner injections while paying for its own infrastructure. Permanent accounting should track original external capital, additional owner capital, equity, realised/unrealised P&L, withdrawals, data/model/server costs, drawdown and return per pound of external capital.

The earlier £25-per-bot/£100 benchmark was a useful conceptual convention but is not the accounting model of the current colony-native run. The implemented paper run instead uses the SOL exposure limits above. Do not mix the two when reporting results.

## Evolutionary objective

Failure is necessary. Weak genomes should lose reproductive opportunity; useful descendants should gain it. But the system must distinguish strategy failure from infrastructure blindness.

A concrete example occurred when the Helius research-credit governor reached its configured 32,000-credit daily ceiling. Wallet observations stopped updating, so wallet-convergence genomes ceased firing while momentum and reversal continued. That is not evidence that wallet convergence failed. The correct response is to repair/optimise the sensor, expose sensor staleness and prevent blind periods from affecting fitness.

The desired causal chain is:

`genome → decision → executable quote → outcome → fitness → reproduction`

The strongest evidence for the architecture would not be one profitable early batch. It would be that fitness measured on past prospective observations predicts performance on unseen future observations, and that later descendants prospectively outperform their ancestors.

## Ecological specialisation

Do not assume one globally superior family must emerge. Different assets and regimes may support different niches: persistent trends may favour momentum; choppy/mean-reverting markets may favour reversal; wallet accumulation may be useful as a separate sensor; cross-sensory descendants may discover combinations that none of the original families encode.

Time horizon may itself evolve. A mature ecology could contain second/minute scalpers, short reversal specialists and longer momentum lineages. Any rapid-trading behaviour must survive realistic spread, slippage, priority fees, failed transactions, latency and adverse selection. High turnover is not rewarded unless net expectancy remains positive after those costs.

Raw win rate is therefore secondary. A 43% strategy can be excellent if its winners dominate; a 60% strategy can be economically useless if its losses are larger. Fitness should focus on expectancy after friction, return distribution and risk.

## Core / Queen

The Core is a small research director, not an unconstrained trader. It consumes compressed state, proposes falsifiable experiments and mutations, identifies underexplored regions and allocates bounded research attention. It does not hold signing authority.

Inference failure is fail-closed. A recent connection failure produced `inference_error`; because no valid Core proposal existed, the Sceptic returned `core_failed` rather than inventing a judgement. Technical failure, genuine Sceptic rejection and successful Queen decisions should be distinct telemetry states.

## Sceptic

The Sceptic independently attacks sample size, multiple testing, leakage, survivorship bias, transaction-cost assumptions, outlier dependence, concentration, regime dependence and weak falsifiability. Its purpose is to force better experiments, not to veto by personality.

A real rejection should contain a valid Core proposal, a substantive Sceptic objection and a deterministic validation outcome. Infrastructure failure is not disagreement.

## Central sensing architecture

External providers feed one central environment rather than every ant independently calling APIs. This keeps costs bounded and gives all genomes comparable evidence. Ants evolve how to interpret observations, not how to purchase data.

The sensor layer should expose facts plus health metadata: values, age, coverage, confidence/provider state. Missing data must be `unavailable/stale`, never silently converted into a meaningful zero.

Additional APIs are most valuable as redundant independent eyes and failover. They should be added after measuring coverage and cost, not simply to compensate for inefficient polling.

## Validation ladder

The intended ladder remains:

Discovery → prospective shadow/paper → frozen out-of-sample paper → tiny live probation → limited live → production.

Promotion must be deterministic and evidence-gated. Candidate criteria include positive expectancy after stressed costs, adequate sample size, acceptable drawdown/tail loss, limited outlier dependence, robustness across regimes and stable behaviour after freezing.

The current experiment is still in prospective paper mode. Real broadcasts remain zero.

## Experimental discipline

Do not tune thresholds because a bloodline is losing. Do not lower qualification standards to create more activity. Do not choose exits retrospectively because they make results attractive. Infrastructure bugs can be fixed, but strategy changes must create a new version rather than rewrite the baseline.

Useful observation checkpoints are approximately 100, 250, 500 and 1,000 marked colony-native bets. At each checkpoint inspect net expectancy after friction, median outcome, profit factor, drawdown, tail risk, consensus size, family/genome separation, regime dependence, correlation and prospective predictive power of fitness.

Early green P&L is interesting but statistically weak. The experiment should be allowed to fail and adapt.

## Capital and blast-radius containment

No ant, Queen or Sceptic controls its own stake. A deterministic allocator/governor owns capital ceilings, paper/live state, exposure limits, loss limits and kill switches. No leverage or averaging-down capability should be introduced casually. Capital increases should be slow and reductions fast.

When real-money probation is eventually justified, it should use genuinely trivial capital. The first purpose of live execution is to test whether paper assumptions survive actual fills, latency, fees and slippage, not to maximise income.

## Graveyard and memory

Failed genomes and experiments should be preserved permanently with exact rules, version hashes, outcomes, market context, objections and retirement reasons. The colony should be able to answer “have we tried this before?” and use autopsies to generate descendants that address identifiable failure modes.

## Near-term engineering priorities

1. Optimise on-chain collection so the wallet sensor consumes fewer Helius credits.
2. Add explicit sensor health/staleness and prevent missing inputs from affecting strategy fitness.
3. Implement real paper-account accounting: starting equity, free cash, open exposure, realised/unrealised P&L, ROI, peak equity and maximum drawdown.
4. Separate OPEN/MTM/CLOSED and eventually allow holding period/exit behaviour to evolve.
5. Feed attributed outcomes back into genome/family fitness and reproduction.
6. Improve Queen inference timeout/failover while keeping fail-closed semantics.
7. Add redundant market/on-chain providers when measured need justifies them.
8. Keep real-money execution disabled until prospective evidence clears fixed promotion gates.

## Core philosophy

Do not build one genius trader.

Build an ecology of tiny, disposable, tightly constrained traders inside a sceptical research-and-risk system.

One nervous system gathers reality. Many simple brains interpret it. Evolution decides which interpretations deserve descendants. The Queen directs research, not money. The governor controls authority. Preserve every failure. Let future data arbitrate every claim.

## Frozen Gen-3 → Gen-4 reproductive constitution (2026-09-26)

This rule is recorded before Gen 4 is permitted to exist. Gen 3 remains the immutable founder baseline (100 genomes: 46 reversal, 33 momentum, 11 wallet convergence, 10 order flow). The purpose is to prevent retrospective movement of the selection target.

Economic success is the ultimate pressure, but raw wins or raw cash alone are not sufficient fitness measures. Selection is based on prospective net economic return after modelled friction, conditioned on capital at risk, downside/tail behaviour and evidence quality. Repeated observations of the same asset cannot manufacture confidence.

Reproductive access is restricted to the top 49% of evidence-qualified performers within comparable ecological niches/families. An ant must first have sufficient independent mature evidence; sparse specialists are not killed merely for trading less often. Family/diversity protection prevents a temporarily dominant high-frequency family from extinguishing rarer useful strategies.

Capital privilege follows evidence slowly and asymmetrically. Proven profitable behaviour can earn incremental increases in maximum notional; poor evidence reduces it; catastrophic/tail-loss behaviour reduces it much faster. New descendants begin in paper probation. No genome, Queen or Sceptic can change global capital ceilings or promote itself to live money.

At each generation checkpoint, weak evidence-qualified performers lose reproductive/live-capital privileges and are demoted to shadow/paper rather than erased. Their genomes and subsequent paper performance remain in the permanent graveyard so regime-dependent strategies can demonstrate renewed usefulness. Catastrophic genomes may be permanently barred from live capital while still retained for research provenance.

At least 5–10% of new-generation capacity is reserved for exploration/mutation rather than direct exploitation of current leaders. This protects diversity and reduces premature convergence on a temporary local optimum.

Gen 4 may only be instantiated after the runtime is stable and the evidence gate is satisfied. Generation creation is a discrete frozen event: calculate Gen-3 fitness using information available at the cutoff, record breeders/culls and hashes, instantiate Gen 4, then evaluate Gen 4 only on observations that occur after its birth. Gen-4 outcomes cannot alter the recorded Gen-3 selection decision.

The primary evolutionary test is not whether Gen 4 makes money in isolation. It is whether descendants prospectively outperform their parents and the frozen Gen-3 baseline after friction and risk. Failure to do so is evidence against the current evolutionary mechanism and must not be hidden by retuning the historical generation.

## Gen-4 constitutional amendment: adversarial controls (2026-09-26)

This amendment is frozen while zero Gen-3 genomes are evidence-qualified and before Gen 4 exists. It strengthens the evidentiary standard without selecting a known winner.

Distinct mint addresses are not treated as independent trials. Qualification requires effective independent evidence across time blocks and market states, with shared SOL beta, volatility/liquidity regime and common routing/liquidity exposure treated as dependence. The original 20-distinct-asset count remains a minimum diversity check, not proof of 20 independent trials. Effective-evidence weighting must be defined/versioned before it can unlock reproduction.

Reproduction requires two gates in order: (1) absolute economic viability after friction/risk/evidence requirements; then (2) relative ranking within comparable viable niches. Family diversity protection cannot force a negative-expectancy family to breed. Non-viable families remain preserved in shadow/graveyard and may requalify prospectively in a later regime.

At every reproductive generation, create a matched random-control population alongside fitness-selected offspring. Gen N+1-E uses the frozen evolutionary selection law; Gen N+1-C is produced without parental fitness information using a recorded random seed and otherwise matched mutation/recombination machinery. Parents continue prospectively as an additional benchmark. All populations receive the same future observations and execution model.

Claims of evolutionary improvement require evolved descendants to outperform both the parent benchmark and matched random-control descendants prospectively after friction/risk. Improvement shared by evolved and control descendants is not evidence that fitness selection caused the gain.

Null benchmarks must include, where technically applicable, random-time, random-direction, market-beta and simple deterministic momentum/reversal controls. Inference must respect temporal/regime clustering and report effect sizes and uncertainty rather than rely on raw trade count or a single p-value. Multiple-comparison/winner's-curse risk from selecting elites must be explicitly included in interpretation.

Experimental provenance is epoch-based. Record code hash, sensor/data schema version, genome constitution version, fitness/selection version, execution-model version, provider configuration and time boundaries. A material change to inputs, decisions, execution economics, fitness or measurement closes the current evaluation epoch and begins a new one. Operational changes proven not to alter experimental semantics do not erase otherwise valid evidence.

No arbitrary correlation cliff (for example correlation >0.7 = one trial), fixed trade-count claim, or hand-labelled number of regimes is constitutionalised here. Dependence and statistical power must be estimated from observed structure and versioned before use. This prevents replacing one naive threshold with another.

## Colony drive model and trust ladder (2026-09-27)

The trading swarm now runs on the same generic eusocial drive model intended for other Grace applications:

`Acquire → Survive → Reproduce → Expand → Fission`

For this colony, resource means realisable net capital after costs. Survival means avoiding catastrophic loss and retaining adaptive capacity. Reproduction means converting validated bloodline success into bounded descendants. Expansion means adding useful, non-redundant workers when evidence and resources justify it.

Every new descendant follows `Birth → Nursery → Paper → Live-ready → Live`. Nursery is cheap QC and broad evidence collection; Paper is deeper prospective validation; Live-ready is eligibility only. Promotion is evidence-gated, not time-gated, so genuinely strong descendants may pass quickly without weakening standards. Real-money authority remains off until externally enabled.

Failed Nursery/Paper descendants are retained as negative knowledge rather than deleted. Matched child-versus-parent evidence measures whether a mutation added value; absolute net expectancy after friction determines whether either lineage deserves scarce capital.

Fission is deliberately visible but practically unreachable at present: £1,000,000 of cumulative realised profit earns eligibility to propose a daughter colony. It does not grant automatic spawn authority. A future daughter Queen would inherit validated genomes and mutation priors, failure/regime/execution memory, and the parent colony's constitutional safety/evidence rules, then begin with a small founding worker group and bounded resource pool in a distinct habitat.

## Bloodline inheritance and negative reproductive memory (2026-09-28)

Descendant promotion now uses the bloodline as its principal evolutionary reference frame rather than requiring every child to beat its immediate parent. Parent-relative comparison remains a local mutation test, but elite parents are not forced into endless improvement.

Paper descendants must first be absolutely viable: positive prospective mean return after the experiment's friction treatment and sufficient prospective evidence. They may then qualify through either of two routes. The bloodline-improvement route requires performance at or above the median prospective return of evidence-qualified mature adults in that family. The elite-inheritance route applies when the parent ranks in the top 10% of evidence-qualified adults: a descendant may preserve elite structure by remaining at or above the bloodline baseline and within 0.5 percentage points of the parent's prospective-window performance.

The governing rule is: weak parents must produce improvement; elite parents may produce preservation or improvement; no descendant is promoted merely because it is less bad than a poor ancestor. Parent comparison is the local mutation test; bloodline performance is the main inheritance benchmark. Thresholds may be revised prospectively as population size and evidence mature, but may not be tuned retrospectively to rescue known descendants.

Reproduction now also maintains active negative memory. Functional descendants receive phenotype fingerprints based on operative parameters rather than mutation provenance. Exact functional duplicates are not regenerated. Evidence-backed failures enter a permanent genome graveyard with lineage, evidence, return and failure reason intact. Repeated nearby failures can make a parameter-space region hostile to future breeding, while isolated failures do not automatically forbid neighbouring exploration. Historical duplicates are retained in research archive but no longer consume new Nursery evidence.

This preserves abundant variation while keeping trust scarce: the colony can explore aggressively, remember what failed, and preserve already-elite structures without rewarding stagnation across the wider bloodline. Real-money authority remains disabled and separate from reproductive status.


## Evolutionary acceleration and elite-only prospective training (2026-09-28)

The colony now treats future market observations as the scarce training resource. Cheap historical compute is used aggressively before a genome is allowed to consume prospective evidence. Each bloodline can generate roughly 10,000 broad historical candidates plus a second elite-directed wave, scored on chronological train/validation splits with a later untouched holdout used only as an audit/veto. Historical success grants permission to audition prospectively; it never counts as forward proof.

Reversal, momentum, order flow and wallet convergence each have an independent tournament with an immortal founder control and the elimination shape `100 → 60 → 30 → 15 → 5 → frozen holdout`. Active prospective training is now elite-only: aside from the immutable baseline/control, random or merely novel nursery organisms are archived but deactivated. Prospective slots are filled only from candidates that clear the historical walk-forward and holdout gates. Replacements begin their prospective record at zero and cannot inherit historical evidence.

The evolutionary accelerator is event-throttled rather than continuously self-mining. It waits for at least 25 new independent mints before rerunning mass historical search, elite-directed breeding, regime-specialist search and generic pattern discovery. This reduces repeated optimisation against the same history and makes new external evidence, rather than CPU cycles alone, the limiting reagent.

A generic pattern miner now searches observed feature combinations and multiple return horizons rather than assuming the hand-authored order-flow hypothesis must be correct. It may nominate a new rule only if it survives chronological evidence gates; returning no robust positive pattern is a valid result. The first strict sweep found no robust generic pattern and no qualified Order Flow elite, which is being treated as evidence that the current feature ecology is insufficient rather than as a reason to relax thresholds.

The same audit exposed and repaired an impossible wallet-convergence threshold. `flow_ratio_15` is calculated as `buys/(buys+sells)` and therefore cannot exceed 1; the previous founder threshold of 1.2 could never fire. The intended 1.2 buy:sell ratio corresponds to a buy-share threshold of approximately 0.545455. Repaired experiments are separated from earlier contaminated evidence.

This changes the optimisation objective from “keep many ants busy” to “spend prospective evidence only on organisms that have earned the right to learn from it.” Broad variation still exists in the historical nursery, but scarce live-paper observation bandwidth is concentrated on controls and elites.

## Elite training roster and challenger queue (2026-09-28)

The prospective layer is now an elite roster rather than a random population. The mass historical nursery can breed very large populations cheaply, but only genomes that survive chronological train/validation screening and an untouched holdout audit are eligible to consume future market evidence. Every bloodline keeps an immortal founder/control.

Qualified genomes beyond current capacity wait in a ranked challenger queue. A queued genome does not replace an active elite simply because its historical result is better. An incumbent becomes replaceable only after at least 12 independent prospective mints and a non-positive prospective tournament score; the challenger must also have a materially stronger historical admission score (minimum +0.01 or +15%).

This makes training slots continuously competitive without contaminating the prospective experiment. The outgoing ant's evidence is preserved permanently, while the incoming challenger receives no inherited prospective credit and must prove itself from zero.

## Stake-aware economics (28 September 2026)

Strategy quality and capital size are now explicitly separated. Each elite is evaluated against a £25 reference paper stake, while fixed round-trip network costs are estimated from the median fee of recently observed successful Jupiter transactions. A trade may therefore retain a strong directional signal while still being labelled uneconomic below its break-even stake. Conversely, increasing stake does not rescue a genuinely negative edge; it only dilutes fixed costs.

Prospective £25 execution-reality probes use actual read-only Jupiter quotes and record stake, measured fixed cost, fixed-cost drag, net £ result and break-even stake. This is a paper/shadow model only; no signing or broadcast capability is introduced.

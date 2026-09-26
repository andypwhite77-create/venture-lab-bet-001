# Grace Evolutionary Trading Swarm

Status: implemented prospective paper experiment
Updated: 2026-09-26

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

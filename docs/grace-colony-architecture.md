# Grace Colony Architecture

Status: implemented prototype / prospective paper experiment
Updated: 2026-09-26

## Purpose

Grace Colony is a reusable architecture for bounded autonomous specialist colonies. The investment colony is the first implemented prototype because market outcomes are measurable. The design separates sensing, evolutionary research, LLM hypothesis generation, deterministic risk/execution, durable memory and human-visible telemetry.

The governing principle is: intelligence may evolve tactics, but it may not evolve authority.

## Implemented hierarchy

External market/data providers feed a central sensing layer. Normalised observations and features form a shared environment consumed by many simple genomes (“ants”). Ants belong to strategy families and independently evaluate opportunities. A small Core/Queen can propose experiments; an isolated Sceptic attacks proposals; deterministic validators and governors decide what is permitted. Execution and capital authority remain outside the LLM layer.

Current strategy families are momentum, reversal and wallet convergence. The forward population observed during the initial live-paper run has been approximately 89 distinct genomes (population changes as the experiment runs), with reversal, momentum and wallet-convergence lineages.

## Data flow

External world → central sensors/collectors → normalised observations/features + sensor health → research candidates → genomes/families → prospective intents → deterministic risk gate → executable market quote → paper ledger → later market marks/outcomes → fitness/evolution.

The intended sensor contract is factual rather than prescriptive. For example, the environment should expose wallet buyer count, flow ratio, observation age and confidence rather than telling ants that “wallet convergence is bullish.” Different genomes can therefore evolve different interpretations of the same evidence.

A key lesson from the running experiment is that sensor unavailability must be distinct from a genuine zero. The Helius wallet feed exhausted a configured 32,000-credit daily research budget, causing wallet-flow observations to collapse. The wallet-convergence family correctly stopped firing, but the system initially represented missing evidence too much like zero evidence. Sensor freshness/availability is therefore now an explicit architectural requirement: blind periods must not be treated as adverse strategy evidence or penalise fitness.

## Colony components

### Core / Queen

A small, intermittent LLM consumes compressed colony state and proposes falsifiable experiments, mutations, novel combinations and research allocations. It does not directly control capital or broadcast transactions. Technical inference failure is fail-closed. A recorded example returned `inference_error` after connection failure; the Sceptic then reported `core_failed` rather than fabricating a review. Timeout/retry behaviour remains operational plumbing to improve.

### Sceptic

A separate adversarial inference role attacks sample size, overfitting, leakage, survivorship bias, transaction-cost assumptions, concentration, regime dependence and weak falsification. A genuine Sceptic rejection is distinct from infrastructure failure and should be displayed separately in telemetry.

### Deterministic evolutionary engine

Ordinary Python/SQL instantiates structured genomes, evaluates prospective candidates, records family/genome lineage, performs controlled mutation/selection and preserves frozen forward tests. Evolution is expressed through populations and durable empirical memory rather than continuous retraining of LLM weights.

### Governor and execution safety

The money layer is deliberately boring. Current colony-native paper intents are simulated only. The initial test uses 0.005 SOL nominal position size and a 0.1 SOL aggregate exposure ceiling. A first batch demonstrated the gate by accepting 19 intents and refusing the twentieth when aggregate exposure reached its limit. The ledger explicitly records `broadcast=false`; no real transaction is implied by paper acceptance.

No genome, Core or Sceptic may increase its own capital ceiling, change paper/live boundaries, obtain signing authority, change global loss limits or alter the constitution.

### Archivist / memory

PostgreSQL stores candidates, forward entries, genomes/lineage-related data, colony events, mind journal, experiments, execution ledger and outcome data. The objective is permanent provenance: what was tried, by whom, under which environment, what happened, and why it survived or died.

## Colony-native prospective experiment

The important transition on 2026-09-26 was from observing external signals to allowing the colony itself to originate paper intents.

Each colony-native intent carries attribution at birth: candidate ID, family, contributing genome IDs, number of agreeing ants and candidate reference/entry information. The system then requests a real executable Jupiter quote, passes the intent through deterministic limits, records it, and later marks it using independent live price data. This creates the causal chain:

`genome(s) → family → decision → executable quote → later outcome → fitness`

Older external wallet-convergence signals remain a separate experiment and are not falsely attributed to individual ants. For those historical signals the dashboard can show contemporaneous family agreement, but that is correlation/endorsement rather than authorship.

## Marking and accounting

“Marked” means an accepted paper position has subsequently been repriced using later live market data and can contribute to calculated P&L. A mark is currently a mark-to-market observation, not necessarily a strategy-defined closed trade. The next accounting layer should explicitly distinguish OPEN, MARKED/MTM and CLOSED and support evolved exits/holding periods.

P&L includes modelled execution friction. The dashboard also converts SOL P&L to a cached live GBP equivalent for human readability. Bloodline cards show both SOL and GBP net results.

The 0.1 SOL figure is presently an aggregate exposure ceiling, not yet a rigorous cash-account ledger. It should therefore not be described as a fully realised “£9 account” return. Planned accounting adds starting equity, free cash, open exposure, realised/unrealised P&L, ROI, peak equity and maximum drawdown.

## Live dashboard

A read-only command centre is deployed at `https://colony.cobaltindustrial.tech/dashboard` behind Caddy/HTTPS. The underlying FastAPI application remains internal. Public routing is intentionally limited to the dashboard and telemetry API; no signing or trading-control endpoint is exposed.

The dashboard displays colony bets, marked outcomes, win rate, cumulative net P&L, GBP equivalent, genome population, real-transaction count, colony-native equity curve, bloodline performance, population, attributed trade tape, Queen/Sceptic journal, experiments/events and the separate external-signal tape. It refreshes approximately every five seconds. The live API was simplified and cached after expensive queries caused the page shell to load while telemetry fields remained blank.

## Infrastructure

The prototype runs as Docker Compose services backed by PostgreSQL. A persistent `paper` service uses `restart: unless-stopped`, so the experiment resumes after container/VPS restart. A Caddy gateway terminates HTTPS. The paper daemon cycles external-signal processing, colony-native intent generation and marking for both streams.

Market/sensor providers currently include Helius-derived on-chain observations, Jupiter executable quotes, Birdeye/CoinGecko-style independent price sensing and CoinGecko SOL/GBP conversion for display. Providers should become redundant where useful; additional APIs are intended to add independent eyes/failover rather than duplicate opinions at the ant layer.

## Evolutionary interpretation

The experiment is not primarily testing whether one hand-designed strategy is profitable. It asks whether selection produces specialists whose fitness on past prospective observations predicts performance on unseen future opportunities.

Different ecological niches are expected to be possible. Momentum may work in persistent trends while reversal works in choppy/mean-reverting assets; wallet flow may act as an upstream feature; cross-sensory descendants may combine evidence. The system should not hard-code that one family is globally superior merely because it leads during a small early sample.

Raw win rate is not the objective. Positive expectancy after realistic friction matters more. A low-win-rate lineage can be profitable if winners dominate losses; a high-win-rate lineage can still destroy capital if its loss distribution is poor.

## Experimental discipline

The running version is treated as a prospective baseline. Do not change thresholds merely because a family is losing, lower qualification standards to make the dashboard active, or retrospectively choose flattering exits. Infrastructure failures may be repaired, but strategy changes must be versioned so they do not rewrite the existing experiment.

Useful checkpoints are approximately 100, 250, 500 and 1,000 marked colony-native bets. Evaluation should include net expectancy after friction, ROI once proper bankroll accounting exists, profit factor, median return, maximum drawdown, tail risk, family/genome performance, consensus strength, regime dependence, correlation and whether descendant fitness predicts genuinely future performance.

The pre-results working hypothesis recorded before the prospective run was that exploitable signal might exist somewhere in the colony, but immediate robust profitability was far from assumed. The stronger result would be evolutionary improvement: descendants prospectively outperforming predecessors without a human manually specifying the winning strategy.

## Constitutional rule

The colony may evolve tactics, parameter sets, strategy families, research allocation and low-risk workers inside predefined limits. It may not autonomously alter capital ceilings, live/paper boundaries, global loss limits, network permissions, secrets, API/model budgets, kill switches, exchange permissions, promotion requirements or its own constitution.

Autonomous reproduction of bounded workers is permitted. Autonomous reproduction of authority is not.

## Next engineering work

1. Optimise Helius/on-chain collection and expose sensor health/staleness explicitly.
2. Prevent missing sensors from being interpreted as genuine zeros or fitness failures.
3. Add rigorous bankroll/equity accounting: cash, exposure, realised/unrealised P&L, ROI and drawdown.
4. Distinguish OPEN, MTM/MARKED and CLOSED; allow exit/holding-period genomes later.
5. Improve Core inference timeout/failover telemetry while preserving fail-closed behaviour.
6. Expand native lineage telemetry through parents/generations and feed outcomes into selection.
7. Add redundant data providers only where measured sensor coverage/cost justifies them.
8. Keep live capital disabled until prospective evidence and promotion gates justify a deliberately tiny probation experiment.

## Central research question

Can a small central intelligence plus adversarial review supervise a population of simple, disposable, tightly bounded agents that discovers robust positive-expectancy behaviour more efficiently than deterministic/random evolution alone?

If the answer survives prospective testing, the architecture is relevant beyond trading: Grace can supervise specialist colonies whose workers are cheap, narrow and replaceable while authority remains deterministic and bounded.

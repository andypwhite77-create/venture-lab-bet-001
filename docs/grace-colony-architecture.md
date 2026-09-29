# Grace Colony Architecture

Status: implemented prototype / prospective paper experiment
Updated: 2026-09-28

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

## Gen-3 → Gen-4 selection law (frozen 2026-09-26)

The first active reproduction law is frozen before Gen 4 exists. Only evidence-qualified ants may enter selection. Reproductive access is limited to the top 49% within comparable niches, ranked primarily by prospective net economic performance after friction and capital-at-risk, with penalties for drawdown/tail loss and controls for evidence quality. Rare/sparse families receive diversity protection; inactivity caused by missing sensors is not failure.

Weak qualified performers are demoted to shadow/paper and retained permanently rather than deleted. Capital privilege rises slowly with demonstrated economic fitness and falls faster after poor/tail outcomes. Descendants begin in paper probation. A 5–10% exploration reserve preserves mutation/diversity. Gen 4 is created at one recorded cutoff and may only be judged on future observations. Global capital limits, live promotion and constitutional authority remain deterministic and cannot evolve.

## Gen-4 adversarial-control amendment (frozen 2026-09-26)

Before Gen 4 exists, the reproductive constitution is strengthened: 20 distinct assets remain a minimum diversity check but no longer imply 20 independent trials. Reproduction is additionally locked behind a versioned effective-independent-evidence model accounting for temporal/regime clustering, SOL beta and shared liquidity/routing exposure.

Absolute economic viability precedes family-relative ranking; diversity protection may preserve a failing family in shadow but may not force it to breed. Every evolved generation must have a matched random-selection control generation and the parent generation must continue as a prospective benchmark. Null controls, block-aware inference, multiple-comparison correction/interpretation and epoch provenance are mandatory before claiming evolutionary improvement.

## Eusocial lifecycle and colony drives (2026-09-27)

The architecture now treats the colony explicitly as a eusocial software organism. The generic motivational layer is:

`Acquire → Survive → Reproduce → Expand → Fission`

Individual ants exist to improve colony-level fitness rather than preserve themselves. Each application defines what counts as resource, survival, reproduction and fission while keeping the core colony machinery reusable.

For the current trading colony, the primary resource is realisable net capital after realistic costs. Survival means avoiding catastrophic loss while preserving adaptive capacity. Reproduction converts validated bloodline success into bounded brood. Expansion adds useful, non-redundant workers when evidence and resources justify it.

New descendants now move through an explicit trust ladder:

`Birth → Nursery → Paper → Live-ready → Live`

Every newborn starts in Nursery. Promotion is evidence-gated rather than time-gated: strong descendants may progress quickly if they accumulate sufficient independent prospective evidence, while uncertain descendants may remain in Nursery indefinitely. Paper is the deeper proving environment. Live-ready means eligible for consideration only; real-money broadcast authority remains externally controlled.

Nursery and Paper failures are preserved rather than erased. Genomes, lineage, observations, matched controls and failure reasons become permanent negative knowledge. Relative improvement over a parent is useful evidence, but it is not enough by itself: a child can beat a poor parent and still have negative absolute expectancy. Absolute net performance after friction remains necessary for scarce capital.

Fission remains a visible long-range drive but has an intentionally extreme threshold. In the trading application, £1,000,000 of cumulative realised profit earns eligibility to propose a daughter colony. It does not spawn one automatically; explicit human authorization remains required.

A future daughter Queen would inherit three classes of compressed memory: genetic memory (validated genomes, bloodlines and mutation priors), cultural memory (failure patterns, regime knowledge and execution lessons), and constitutional memory (safety rules, evidence standards, resource limits and promotion gates). It would receive a small founding worker group and a bounded resource pool, then operate the same Acquire → Survive → Reproduce → Expand cycle in a distinct habitat.

This makes the colony architecture reusable beyond trading: the domain supplies the resource and reproductive definitions; the colony supplies the motivational, evidentiary and constitutional machinery.

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

## Elite-only prospective training and challenger pressure (2026-09-28)

The architecture now distinguishes unlimited cheap candidate generation from scarce prospective training capacity. Historical nurseries may generate and slaughter thousands of genomes, but only walk-forward-qualified, untouched-holdout-surviving elites may consume new market observations. Each bloodline preserves an immortal founder/control.

When a bloodline is full, newly qualified elites enter a ranked challenger queue rather than being discarded. Historical score alone is never sufficient to evict an incumbent: the incumbent must first accumulate at least 12 independent prospective mints and have a non-positive prospective tournament score. The challenger must also exceed the incumbent's historical admission score by at least 0.01 or 15%, whichever is larger. Baselines are never displaced.

If turnover occurs, the incumbent is archived with its prospective evidence and a `challenger_displacement` reason; the challenger starts prospective evidence from zero. Empty slots are still filled immediately from the strongest qualified queue. This preserves forward-test integrity while ensuring active training capacity remains contestable by newly discovered high performers.

## Stake-aware execution economics (28 September 2026)

The colony now treats £25 as the per-ant reference stake for eventual canary-scale economics. Fitness distinguishes signal return from stake-dependent execution viability. Fixed costs are estimated from observed on-chain Jupiter fees, while proportional friction and quote-derived price impact remain separate. The model can therefore identify a minimum break-even stake for a good signal instead of misclassifying it as a bad strategy solely because a toy stake cannot absorb fixed fees.

A new prospective execution epoch probes elite-family opportunities at approximately £25 equivalent SOL using read-only Jupiter quotes. The epoch begins after candidate 1395 so earlier observations are not retrospectively backfilled. All execution remains simulated and broadcast authority remains off.

## Breed, test, take the best

The governing evolutionary rule is simple: breed descendants, test them prospectively on independent opportunities, and retain only the strongest evidence-backed performers. Paper evidence is cheap, so selection must favour proof over speed.

Reversal uses increasingly demanding cumulative gates: 20 independent mints before 100→60, 40 before 60→30, 60 before 30→15, and 80 before 15→5. The final five are then frozen and must survive 50 entirely new independent mints. Historical/backtest strength cannot substitute for prospective evidence.

Children are judged primarily against the bloodline and also against their parent window. Weak parents must produce genuine improvement. Elite parents may produce descendants that preserve strong expectancy while improving robustness, tail behaviour, drawdown, execution quality, or regime coverage. No descendant advances merely because it is less bad than a weak parent.

Selection rewards net expectancy after costs, control/baseline edge, consistency and robustness, while penalising tail loss, drawdown, outlier/moonshot dependence and excessive correlation with stronger relatives. Failed descendants are archived/demoted; they do not receive live capital. Live-ready remains eligibility only and cannot grant itself execution authority.

## Historical slaughterhouse -> production pool

For Reversal, broad breeding is intentionally cheap and massive: 50,000 historical variants per acceleration cycle. Chronological training and validation select; an untouched historical holdout can veto but is never optimised against. Only ten historically robust/diverse survivors consume prospective evidence.

Those ten then face real future market data in paper mode. At 20 independent mints, only candidates with positive mean and median net return, positive matched edge to the immortal control, acceptable tails and the strongest correlation-adjusted scores may enter the production pool; at most five are admitted. Parents are retained. Production-pool membership means eligible for the main/live-ready ecology, never autonomous permission to broadcast real-money trades.

The research bank grows continuously: raw prospective candidates/outcomes/price paths/snapshots remain retained, while a dedicated archival worker backfills hourly Solana pool OHLCV from GeckoTerminal for observed pairs. External historical sources are discovery data, not promotion evidence.

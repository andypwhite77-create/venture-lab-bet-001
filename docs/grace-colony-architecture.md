# Grace Colony Architecture

## Purpose

This document defines a reusable architecture for autonomous specialist colonies that can eventually sit beneath Grace.

The central idea is that Grace should not need infinite resources or one giant model. She should be able to assign a bounded goal, rules, permissions and resources to a small specialist colony running on inexpensive infrastructure. The colony then works largely independently, reports compressed state upward, and escalates only when required.

The investment colony is the first prototype because its outcomes are measurable and the current Venture Lab system already provides market ingestion, experiment tracking, paper trading, outcomes, price paths and monitoring.

## Hierarchy

Grace is the executive intelligence.

Her council provides cross-domain executive functions such as:

- Archivist: durable memory, provenance and retrieval.
- Sceptic: challenges assumptions and weak reasoning.
- Security Guard: permissions, secrets, network boundaries and kill switches.
- Auditor: checks whether claimed results are supported by evidence.
- Planner: allocates goals, work and resources.

Beneath Grace sit specialist colonies. Each colony is semi-autonomous inside a fixed constitution.

Examples:

- Investment Colony
- Opportunity / Employer Outreach Colony
- Research Colony
- Software / Operations Colony
- Future specialist colonies as useful domains emerge

Grace should not need to understand each colony's low-level tactics. She should receive health, findings, requests, risks and escalations in a standard format.

## Standard Colony Components

Every colony should contain five core layers.

### 1. Core Intelligence

A small LLM whose job is not to perform every task itself, but to direct research and generate experiments.

For an investment colony, it should:

- ingest compressed market and experiment summaries;
- identify promising or underexplored regions;
- propose falsifiable hypotheses;
- generate new strategy genomes or mutations;
- decide where research effort should be concentrated;
- learn from successful and failed descendants;
- avoid repeatedly recreating previously failed ideas.

The core intelligence should not directly execute trades or control risk limits.

### 2. Mini-Sceptic

A separate model instance whose only purpose is to attack proposals.

It should look for:

- small-sample effects;
- overfitting;
- look-ahead leakage;
- survivorship bias;
- hidden correlation with existing strategies;
- unrealistic transaction-cost assumptions;
- regime dependence;
- profit concentration in one or two outliers;
- repeated testing of essentially identical hypotheses;
- inadequate falsification criteria.

The sceptic is not required to be right. Its job is to make weak ideas uncomfortable and force experiments that could disprove them.

### 3. Deterministic Experiment Engine

This should be ordinary software rather than an LLM.

Responsibilities:

- instantiate strategy genomes;
- evaluate incoming data;
- create scouts, challengers and contenders;
- collect outcomes;
- calculate performance statistics;
- apply promotion and retirement rules;
- enforce experiment versions;
- ensure forward tests remain frozen once started.

### 4. Archivist / Colony Memory

Persistent structured storage should contain every experiment, lineage, result, objection and retirement reason.

Suggested tables include:

- colony_genomes
- colony_experiments
- colony_lineage
- colony_reviews
- colony_resource_budget
- colony_graveyard
- market_regimes
- promotion_events
- retirement_events
- allocation_history

The archive should make it easy to answer "Have we already tried this?" and to prevent the system from rediscovering the same failed idea indefinitely.

### 5. Governor

The governor is deterministic and cannot be overridden by the core intelligence.

It owns:

- resource limits;
- capital limits;
- permissions;
- live/paper boundaries;
- model/API budgets;
- kill switches;
- promotion requirements;
- exposure limits;
- allowed exchanges and data sources.

The colony may evolve strategies. It may not evolve its constitution.

## Model Requirements

The colony does not require a large frontier model for continuous operation.

A sensible starting architecture is:

- Core intelligence: small 7B-14B class model or inexpensive hosted equivalent.
- Mini-sceptic: separate small model or separately isolated instance, ideally with different context and possibly a different model family.
- Statistics, scoring, ranking and execution: Python/SQL, not LLM reasoning.

The core model mainly performs synthesis and hypothesis generation. It should consume summaries rather than raw tick data.

A typical prompt might contain:

- current market regime;
- experiment family performance;
- unresolved sceptic objections;
- underexplored feature combinations;
- recent failures;
- current research budget;
- novelty requirements.

The core then returns structured hypotheses rather than prose trading advice.

## Infrastructure

### Cheap Hosted-Inference Colony

Likely starting point:

- low-cost VPS in roughly the £10-£20/month range;
- 4 vCPU;
- 8 GB RAM;
- 80-160 GB SSD;
- PostgreSQL;
- Python/FastAPI;
- lightweight queue or Redis if useful;
- all deterministic workers local;
- occasional model calls to a cheap hosted inference API.

The LLM does not need to run continuously. It can wake periodically, consume summaries, generate the next batch of experiments, debate with the sceptic and return to sleep.

### Fully Local Colony

If avoiding hosted inference becomes desirable, a practical CPU-first machine would be closer to:

- 8-12 decent CPU cores;
- 32 GB RAM;
- NVMe storage;
- quantized 7B-14B model via a local runtime;
- optional GPU only if speed later becomes important.

Because colony reasoning jobs are intermittent, latency is far less important than cost and reliability.

## How the Colony Learns

The system should not initially self-improve by constantly retraining model weights. Instead, learning should happen through structured memory, selection and adaptation.

### Empirical Memory

Every experiment becomes permanent data.

A record should include:

- experiment ID;
- parent ID;
- strategy family;
- complete genome;
- hypothesis;
- market regime;
- sample count;
- return distribution;
- drawdown;
- cost sensitivity;
- sceptic objections;
- validation results;
- status;
- retirement reason.

The model improves because its searchable world becomes richer.

### Evolutionary Learning

Strategies should be represented as structured genomes rather than arbitrary code wherever possible.

Example genome:

```text
family = reversal
lookback = 5m
shock_min = -14%
shock_max = -8%
buy_ratio_min = 0.62
liquidity_min = 100000
max_hold = 18m
stop = -5%
target = +7%
```

Successful parents can produce descendants by controlled mutation.

Example:

```text
PARENT C17
├── C42 liquidity > £120k
├── C43 liquidity > £180k
├── C44 stop -4%
└── C45 target +8%
```

Each descendant begins independently in paper mode.

### Policy Learning

The colony should learn where research resources are productive.

If one family repeatedly produces useful descendants and another produces little signal, the research budget can gradually shift toward the productive family while preserving mandatory exploration elsewhere.

This can be handled using simple statistical allocation or multi-armed-bandit style logic rather than LLM intuition.

The LLM may propose allocations, but deterministic rules should enforce limits such as:

- maximum share of research budget per family;
- minimum novelty budget;
- minimum exploration budget;
- uncertainty adjustments for small samples.

## Evolution Mechanisms

The colony should support four main ways to create descendants.

### Mutation

Small changes to a successful parent genome.

Examples:

- slightly different entry threshold;
- different liquidity floor;
- different hold period;
- different stop or target.

### Crossover

Combine useful traits from two successful families where this is logically coherent.

Crossover should be used cautiously because it can rapidly create a huge search space.

### Novelty

The core intelligence proposes a genuinely new hypothesis or feature family.

A fixed portion of research capacity should always be reserved for novel ideas so the system does not converge prematurely on one local optimum.

### Autopsy-Driven Creation

Failures should produce descendants designed to address the identified failure mode.

Example:

If many reversal strategies fail by catching falling knives before demand returns, the colony may create a new branch requiring explicit recovery confirmation before entry.

This turns failure history into useful accumulated knowledge.

## Population Structure

Not every experiment needs to be a full autonomous bot.

### Scout

A cheap probe that tests a narrow relationship for hours or days.

Example:

"Record every token meeting X, Y and Z and measure returns at 3, 5, 10, 20 and 60 minutes."

Hundreds of scouts can be represented as rows in a database and evaluated by common workers. They do not need individual processes or servers.

### Challenger

A hypothesis that survived initial screening and now generates proper prospective paper trades.

### Contender

A frozen strategy undergoing promotion-quality forward testing.

### Live Probation

A strategy that passed the promotion gate and is allowed only a tiny amount of real capital under hard deterministic controls.

### Live Trader

A strategy with demonstrated forward performance that still remains subject to allocation, drawdown and retirement rules.

An eventual mature colony might contain hundreds of scouts, tens of challengers, a smaller number of contenders and a limited number of live traders.

## Selection and Competition

The system should operate as an evolutionary league.

A possible early population is:

- 6 live traders;
- 10 paper traders;
- a much larger pool of cheap scouts.

The bottom paper performers are periodically retired and replaced with new descendants or novel hypotheses.

Raw weekly P&L should not determine survival by itself. Scoring should include:

- net expectancy after costs;
- median return;
- profit factor;
- drawdown;
- tail risk;
- trade frequency;
- sample size;
- cost sensitivity;
- regime stability;
- profit concentration;
- correlation with existing live traders.

New strategies need a minimum observation period or sample count before they can be culled or promoted.

The strongest paper contender may challenge the weakest live trader, but promotion should require a fixed gate rather than simple relative ranking.

As the colony proves itself, capacity can expand from approximately 6 live / 10 paper to 10 live / 15 paper and later larger populations.

Population growth should happen because the ecosystem has earned the ability to support it, not simply because more bots sound exciting.

## Dynamic Capital Allocation

Live bots should not control their own stake.

A separate allocator sets allowed position size based on deterministic health metrics such as:

- recent expectancy;
- rolling profit factor;
- rolling median return;
- drawdown;
- loss streak;
- return volatility;
- liquidity and slippage;
- sample size;
- similarity to validated historical behaviour;
- total colony exposure.

Capital increases should be slow. Reductions should be fast.

Example tiering:

```text
base stake: £10
strong state: £15
very strong state: £25
exceptional state: £50 maximum

one loss: step down one level
second consecutive loss: return to base
hard drawdown breach: disable live trading and return to paper
```

Exact values would be determined later from evidence rather than hard-coded assumptions.

No bot may increase its own capital ceiling.

## Self-Funding Colony

The long-term experiment is not merely whether the system can produce profit. It is whether a tiny amount of external capital can grow without repeated owner injections.

The original starting capital should remain permanently tracked.

Example accounting:

```text
External capital introduced: £100
Additional owner capital: £0
Current equity: £X
Cumulative withdrawn profit: £Y
```

Successful live bots can retain some earnings for growth while contributing some profits to a colony treasury.

The treasury can eventually fund new probation bots, data, compute and model costs.

The ideal loop is:

```text
small initial colony capital
→ profitable ants
→ colony treasury
→ new probation ants
→ successful descendants compound
→ larger treasury
```

Capital efficiency is therefore a core metric, not merely headline P&L.

## Sceptic Debate Protocol

The sceptic should receive a narrow packet:

```text
PROPOSAL
EVIDENCE
ASSUMPTIONS
EXPECTED TEST
RESOURCE COST
```

It should return:

```text
FATAL OBJECTIONS
MAJOR OBJECTIONS
MINOR OBJECTIONS
REQUIRED FALSIFICATION TESTS
```

The core intelligence then answers those objections.

Certain classes of sceptic objections should deterministically block promotion until resolved.

Example:

```text
SCEPTIC:
Historical selection bias is probable.

CORE:
Freeze the strategy and run only on data beginning tomorrow 00:00 UTC.

VALIDATOR:
Accepted. Status = forward-paper-test.
```

The debate should therefore generate better experiments rather than endless argument.

## Daily Operating Cycle

### Continuous

- ingest market/data streams;
- evaluate scouts;
- generate paper trades for challengers;
- record outcomes and paths;
- update deterministic statistics.

### Hourly

- refresh family statistics;
- terminate obviously invalid cheap scouts;
- flag unusual findings;
- update health and resource state.

### Every Few Hours

- core intelligence wakes;
- reads compressed colony state;
- proposes new experiments;
- sceptic attacks proposals;
- core responds;
- validator accepts or rejects proposed experiments;
- approved genomes enter the research queue.

### Daily

- review population health;
- adjust research allocation;
- inspect regime changes;
- update novelty/exploration budgets.

### Weekly

- formal selection event;
- retire weak strategies;
- consider promotion of strong contenders;
- review lineages and graveyard;
- generate replacements;
- review whether population capacity has earned expansion.

## Information Compression

The core intelligence should not receive raw tick history.

It should receive a compressed state such as:

```text
Market regime:
high volatility
small-cap liquidity deteriorating

Reversal family:
83 active experiments
12 promising
4 independently replicated

Momentum family:
64 experiments
2 promising
median expectancy negative

Unexpected finding:
wallet accumulation + liquidity recovery
positive 15m expectancy
N=47

Recent failures:
15 killed by cost sensitivity
8 killed by concentration
```

This keeps model cost low and encourages reasoning about experiments rather than drowning in raw data.

## Grace Interface

Every colony should eventually expose the same small control surface.

Suggested interface:

```text
GET /health
GET /summary
GET /findings
GET /resource-request
GET /escalations
POST /goal
POST /pause
POST /resume
POST /constitution
```

Grace should receive executive-level state such as:

```text
INVESTMENT COLONY
status: healthy
goal: discover low-capital short-horizon edges
scouts: 487
challengers: 18
contenders: 4
live: 0
best family: liquidity shock reversal
research confidence: medium-low
major sceptic objection: regime dependence
resource request: none
human action required: none
```

Grace only drills down when needed.

## Constitutional Rule

A colony may evolve its tactics, experiments and strategy population.

It may not autonomously alter its authority.

It must not be able to change:

- capital ceilings;
- live/paper boundaries;
- global loss limits;
- network permissions;
- secret access;
- model/API budget;
- kill-switch behaviour;
- exchange permissions;
- promotion requirements;
- its own constitution.

Autonomous reproduction of low-risk workers is permitted inside predefined limits. Autonomous reproduction of authority is not.

## Recommended Build Sequence

### Phase 1 — Colony Memory

Add durable genome, experiment, lineage, review, resource and graveyard storage to the existing Venture Lab system.

### Phase 2 — Genome Engine

Represent the current four strategy families as structured parameterized templates.

### Phase 3 — Deterministic Evolution

Automatically generate controlled mutations and test them prospectively in paper mode.

No LLM is necessary yet.

### Phase 4 — Selection League

Add population scoring, retirement, promotion and fixed forward-test gates.

### Phase 5 — Mini-Sceptic

Introduce adversarial review and require falsification tests for suspicious hypotheses.

### Phase 6 — Small Core Intelligence

Allow a small model to propose research allocation, mutations and novel hypotheses using compressed colony state.

### Phase 7 — Grace Integration

Expose the standard colony API and place the investment colony beneath Grace's governance.

### Phase 8 — Tiny Live Probation

Only after sufficient prospective evidence, add tightly bounded live capital under deterministic risk control.

## First Major Experiment

Before the LLM is added, let deterministic evolution run against the same research environment.

Then add the core intelligence and sceptic and compare the two systems.

The central question is:

> Does a tiny intelligence at the centre of the colony help the swarm discover robust edges faster or more efficiently than deterministic/random evolution alone?

That experiment is valuable beyond trading. If the answer is yes, it validates a central architectural principle for Grace: cheap specialist intelligence can supervise large populations of narrow workers inside bounded autonomous colonies.

# Grace Evolutionary Trading Swarm

Status: concept / architecture note
Date: 2026-09-25

## Core idea

Turn the current Solana paper-trading experiment into an evolutionary swarm of many small, tightly constrained trading bots coordinated by Grace.

The goal is not to build one giant AI trader. The goal is to build a research-and-allocation system that continuously discovers, challenges, tests, promotes, scales down, retires, and replaces small strategy bots.

Intelligence lives at the colony level. Individual bots stay deliberately simple.

## Economic objective

The experiment starts from a deliberately tiny amount of external capital.

The long-run ideal is:

- bots begin with tiny allocations such as £25;
- successful bots compound their own capital rather than requiring repeated owner injections;
- profitable bots contribute part of profits to a colony treasury;
- the treasury funds new probationary bots;
- the swarm grows primarily from internally generated capital;
- external capital introduced remains tiny relative to eventual equity and withdrawals.

The important accounting metrics should therefore include:

- original external capital introduced;
- additional owner capital introduced;
- current colony equity;
- cumulative realised profit;
- cumulative withdrawn profit;
- total infrastructure/data/model costs;
- net system income after all costs;
- return generated per £ of external capital introduced.

The original £100 benchmark should remain visible permanently even if the system grows far beyond it.

## Current benchmark convention

For human-readable updates, maintain a running hypothetical benchmark in which each core bot began with £25.

Unless deliberately changed later, use the same fixed 15-minute exit convention for comparability and include assumed trading friction.

Each update should include:

- £25-per-bot running balances;
- total £100 benchmark balance;
- trade count per strategy;
- current best and worst behaviours;
- emerging patterns worth watching;
- explicit warning when sample sizes remain small.

## Grace as research director

Grace should not directly improvise live trades.

Grace's role is to:

1. ingest observed market and bot data;
2. identify candidate patterns;
3. formulate falsifiable strategy hypotheses;
4. generate a precise strategy specification;
5. submit it to adversarial review;
6. spin up a paper-only bot when approved;
7. monitor forward performance;
8. promote, demote, retire, or replace bots under deterministic rules.

A proposed strategy should include at minimum:

- strategy/version ID;
- entry conditions;
- exit conditions;
- stop conditions;
- maximum holding time;
- liquidity requirements;
- cost/slippage assumptions;
- sample on which the idea was discovered;
- status: untested, paper, probation, live, reduced, retired.

## The Sceptic

Grace includes a separate sceptic LLM whose job is to disagree with proposals and force Grace to reason its decisions.

The sceptic should attack:

- sample size;
- overfitting;
- multiple-hypothesis/data-mining bias;
- leakage/look-ahead bias;
- survivorship bias;
- transaction-cost assumptions;
- slippage assumptions;
- dependence on one or two outliers;
- concentration in one token, liquidity bucket, hour, day, or regime;
- fragile parameter choices;
- alternative explanations;
- poor falsifiability.

The sceptic's purpose is not to be right. Its purpose is to make weak ideas uncomfortable.

Grace must answer objections with evidence. Where possible, the sceptic should propose explicit falsification tests rather than generic criticism.

Important design principle: the sceptic should be as independent from Grace's prior reasoning and enthusiasm as practical, reducing anchoring.

## Validation and promotion ladder

A strategy should never move directly from discovery to live money.

Suggested ladder:

Discovery
→ historical hypothesis
→ shadow/paper test
→ frozen out-of-sample paper test
→ tiny live probation
→ limited live
→ production

Promotion must depend on both elapsed time and number of qualifying trades. A week containing only a handful of trades is not sufficient evidence.

Promotion criteria should be deterministic and auditable, not based on an LLM's confidence alone.

Candidate criteria may include:

- positive net expectancy;
- positive median return;
- profitability after stressed transaction costs;
- minimum sample size;
- acceptable maximum drawdown;
- acceptable tail loss;
- no dependence on a single exceptional winner;
- acceptable profit factor;
- performance across different hours/days/regimes;
- stable behaviour after rules are frozen;
- successful forward/holdout performance.

## Dynamic capital allocation

Bots should not decide their own stake size.

A separate allocator/risk engine controls capital.

Example capital ladder:

- base: £10;
- strong: £15;
- very strong: £25;
- exceptional: £50 maximum.

The exact values are placeholders and should be evidence-based later.

Sizing should consider more than win streaks. Inputs may include:

- rolling expectancy;
- rolling median return;
- rolling profit factor;
- maximum drawdown;
- current loss streak;
- volatility of returns;
- liquidity quality;
- realised slippage;
- sample size in the current window;
- deviation from validation-period behaviour;
- overall colony exposure.

Capital increases should be slow and capital reductions fast.

For example, a bot might need many strong trades to move upward but only one or two significant losses, a drawdown breach, or abnormal behaviour to step down quickly.

## Blast-radius containment

Assume every bot can eventually be wrong, buggy, compromised, overfit, or exposed to the wrong regime.

Each bot therefore gets a deliberately tiny blast radius.

Possible controls:

- hard per-trade cap;
- hard daily loss cap;
- hard total drawdown cap;
- no leverage by default;
- no averaging down;
- no permission to change its own risk limits;
- no access to the master treasury;
- no ability to grant itself more authority;
- automatic disable on anomalous behaviour;
- forced return to paper after specified breaches.

Cultural/logging convention:

`BOT_37_ROGUE_TRADE_ERROR -> SHOOT_BEHIND_SHED`

This means isolate/disable the bot, preserve telemetry, diagnose the cause, and prevent recurrence. It is deliberately humorous language for a very real containment policy.

## Distributed swarm architecture

If the system grows, distribute it across several small servers/regions/providers for resilience and isolation.

Benefits:

- one server failure does not stop the colony;
- one compromised machine cannot reach all capital;
- strategy families can be isolated;
- deployments can be staged;
- operational risk is compartmentalised.

The system should remain fully auditable and compliant. Distribution is for resilience and containment, not concealment.

Possible layout:

Grace / Sceptic / Validator
→ policy engine
→ capital allocator
→ multiple isolated strategy servers
→ tiny deterministic bots
→ broker/exchange execution layer

Each server should receive only the credentials and permissions it absolutely needs.

## Evolutionary population model

The swarm should have a finite number of live trading slots and paper-testing slots.

Initial concept:

- 6 live traders;
- 10 paper traders.

Every evaluation cycle, paper bots compete for survival and promotion.

The bottom two paper bots are retired and two new bots are developed from fresh hypotheses.

Do not rank bots only by raw weekly P&L. That would overreward luck and punish lower-frequency strategies.

A paper-bot fitness score should consider:

- net expectancy after costs;
- median return;
- drawdown;
- tail risk;
- consistency;
- profit factor;
- sample size;
- dependence on outliers;
- regime diversity;
- capital efficiency.

New bots should receive a protected minimum trial period and/or minimum number of qualifying trades before they can be culled.

The strongest paper bot may challenge the weakest live bot, but promotion still requires passing a fixed promotion gate. Being first in a bad cohort is not enough.

Retired bots should go into a permanent graveyard rather than being deleted.

The graveyard should preserve:

- exact rules;
- strategy/version hash;
- all results;
- reason for retirement;
- market conditions/regime;
- sceptic objections;
- failed validation tests.

This prevents Grace from accidentally reinventing failed strategies later.

## Population growth

The colony expands only after the existing population proves stable enough to support it.

Example stages:

Seed colony:
- 6 live;
- 10 paper.

Established colony:
- 10 live;
- 15 paper.

Possible later mature colony:
- 20 live;
- 30 paper.

Expansion is evidence-gated rather than ambition-gated.

The preferred scaling path is breadth before size: find more genuinely independent edges before massively increasing capital behind one strategy.

## Strategy independence

Multiple bots only provide real diversification if their edge drivers are genuinely different.

Five copies of the same reversal strategy are effectively one bet wearing five hats.

The system should prefer diversity across:

- strategy family;
- time horizon;
- data source;
- market regime;
- market/instrument;
- execution style;
- signal driver.

## The research factory model

The long-term target is not one magical strategy.

The target is a machine that continuously manufactures small, boring positive-expectancy strategies.

Grace finds experiments.
The Sceptic attacks them.
The Validator enforces fixed evidence rules.
Paper bots collect forward evidence.
Probation bots receive tiny real allocations.
The allocator slowly rewards durable performance.
Weak bots are starved, demoted, or retired.
Successful bots fund the next generation.

## Guard against false discovery

An autonomous system capable of testing thousands of patterns will inevitably discover apparently amazing patterns by chance.

Therefore:

- exploratory data and validation data must be separated;
- once a rule enters forward validation it should be frozen;
- strategy/version fingerprints should be stored permanently;
- holdout sets should be used where practical;
- future data should be the ultimate arbiter;
- multiple-testing bias must be treated as a core system risk;
- parameter robustness matters more than finding the single best historical parameter;
- every promoted strategy should survive harsher-than-expected costs and slippage.

The guiding principle is: you cannot overfit tomorrow.

## Grace intelligence vs execution intelligence

Grace may be imaginative at the research layer.

The money layer should be deliberately boring.

A deterministic execution bot should do little more than verify that:

- the strategy is approved;
- the signal is valid;
- capital is available;
- exposure is below limits;
- daily loss is below limits;
- liquidity/slippage checks pass;
- the exact pre-approved trade is still valid.

Otherwise it does nothing.

The component holding money should never have free-form authority to invent a new action.

## Live probation concept

If paper performance remains stable through the planned observation period, the first live trial should use genuinely trivial capital.

Example concept discussed:

- £25 total starting live capital;
- tiny per-trade caps;
- no leverage;
- no averaging down;
- hard daily loss limit;
- automatic return to paper on abnormal behaviour;
- no bot can increase its own allocation.

The point is not to prove profitability quickly. The point is to validate that paper assumptions survive contact with real execution, fees, fills, latency, and slippage without creating meaningful financial risk.

## Milestone philosophy

Minimum-wage-equivalent income is considered a gold-standard long-run outcome, not a near-term expectation.

At £12/hour continuously, 24/7 would be £2,016/week before tax and running costs, so even fractions of that would be economically meaningful.

Suggested progression:

- pay its own server/data/model costs for three consecutive months;
- produce £100/month net;
- produce £250/month net;
- continue upward only if returns remain durable and risk limits do not loosen;
- treat minimum-wage-equivalent net income as a major mature-system milestone.

Measure net system income after fees, slippage, data, servers, model/API costs, and losses from retired bots.

## Core philosophy

Do not build one genius trader.

Build a colony of tiny, disposable, tightly constrained traders under a sceptical research-and-risk system.

Intelligence at the colony level.
Simplicity at the ant level.
Increase slowly.
Decrease quickly.
Preserve every failure.
Make every promotion earn its capital.
Let profitable generations fund the next generation.

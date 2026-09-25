# Venture Lab Bet 001 — Multi-Strategy Solana Research Engine

Venture Lab Bet 001 is a live-market, **paper/shadow-trading research platform** for testing whether public Solana activity contains repeatable trading edges after realistic friction.

It began as a single wallet-convergence experiment and now runs four distinct strategy families against shared blockchain and market data. The system records both trade-grade signals and sub-threshold observations, measures forward returns at fixed horizons, and maintains a common scoreboard so strategies can be compared without changing the rules after the fact.

The project is intentionally research-first. It does **not** contain live-order execution and it refuses to start unless `PAPER_TRADING_ONLY=true`.

## Core objective

The goal is not maximum trade frequency. The target is a small number of economically meaningful opportunities per day with positive net expectancy after fees, slippage and failed signals.

The development sequence is:

1. collect live data;
2. generate candidate events prospectively;
3. record an executable reference price at the time of the event;
4. measure what happened later without backfilling future information;
5. compare strategy variants on a common scoreboard;
6. reject weak ideas quickly;
7. only consider tiny real-money testing after a strategy has earned it on forward data.

## Current architecture

```text
                     PUBLIC LIVE DATA
                           |
            +--------------+--------------+
            |                             |
      Solana / Helius              GeckoTerminal
      Jupiter activity             token + pool data
            |                             |
            +--------------+--------------+
                           |
                    SHARED DATA LAYER
                           |
        +------------------+------------------+
        |                  |                  |
 observed_transactions   wallets       market_snapshots
        |                                     |
        +------------------+------------------+
                           |
                    STRATEGY ENGINE
                           |
       +---------+---------+---------+---------+
       |         |         |         |         |
     Bot A     Bot B     Bot C     Bot D      future
    wallets   flow      reversal  momentum    bots
       |         |         |         |
       +---------+---------+---------+
                           |
                 research_candidates
                           |
              prospective shadow trades
                           |
                   FORWARD EVALUATOR
                           |
                  research_outcomes
                           |
                      SCOREBOARD
```

## Safety / research guardrails

The current build has deliberately hard boundaries:

- paper/shadow trading only;
- no private keys;
- no exchange credentials;
- no transaction signing;
- no leverage or borrowing;
- no real order submission;
- conservative assumed round-trip friction on research trades;
- RPC credit budgets with hard stops;
- candidate deduplication/cooldowns to prevent the same condition being counted every minute;
- forward outcomes are measured after the event rather than retroactively selecting good historical examples.

`app.py` aborts startup if `PAPER_TRADING_ONLY` is not `true`.

## Data sources

### Helius Solana RPC

Helius supplies Solana RPC data. The collector samples recent Jupiter v6 activity rather than trying to index the entire chain.

The research build currently calls:

- `getSlot` for heartbeat/chain health;
- `getSignaturesForAddress` against the Jupiter v6 program;
- `getTransaction` for sampled signatures.

RPC use is metered internally in `budget.py`. Archival-style calls are deliberately costed conservatively for budget accounting.

### Jupiter activity

`collector.py` samples transactions involving the Jupiter v6 program:

`JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4`

Each sampled transaction is normalised into:

- signature;
- slot;
- block time;
- signer wallet;
- source program;
- fee;
- success/failure;
- native SOL delta;
- signer-owned token deltas;
- lightweight transaction metadata.

The collector supports versioned Solana transactions through:

```python
"maxSupportedTransactionVersion": 1
```

### GeckoTerminal

GeckoTerminal is currently used for public market information without requiring trading credentials.

Two types of request are used:

1. multi-token snapshots for contemporaneous USD prices of wallet/flow candidates;
2. Solana trending-pool data for the market-wide reversal and momentum strategies.

Trending pool snapshots provide fields such as:

- USD price;
- pool liquidity;
- 5-minute and 1-hour volume;
- 5-minute and 1-hour price change;
- recent buy/sell transaction counts;
- market cap / FDV where available;
- DEX and pool identifiers.

This allows Bots C and D to operate independently of the sparse wallet sampler.

## Database

PostgreSQL 16 runs in Docker with a persistent named volume.

### Core tables

`rpc_samples`

Records successful chain heartbeat slots.

`wallets`

Tracks discovered wallet addresses, source, first/last seen timestamps, transaction counts and swap-like activity.

`observed_transactions`

Stores sampled Solana transactions and token deltas.

`signal_events`

Legacy/first-generation wallet-convergence signals.

`signal_outcomes`

Forward measurements for the original signal engine.

`paper_trades`

Reserved first-generation paper-trade table. The v1 multi-strategy research platform uses `research_candidates` and `research_outcomes` as its canonical forward-test record.

`engine_events`

Operational/startup/error events.

`rpc_usage`

Estimated Helius call/credit usage.

### Research tables

`research_candidates`

Every candidate produced by Bots A-D. Important fields include:

- strategy;
- mint;
- direction;
- numeric score;
- `tier` (`observe` or `trade`);
- `shadow_trade` boolean;
- contemporaneous entry price;
- assumed friction;
- full feature JSON;
- market snapshot JSON.

An `observe` candidate is deliberately retained even when it is not strong enough to become a paper trade. This is essential: otherwise the engine would throw away the near-misses needed to discover better thresholds later.

`research_outcomes`

Forward performance of every candidate that had a contemporaneous entry price, including both `observe` and `trade` tiers. This is what allows sub-threshold ideas to be compared with the live paper-trade rules later.

Current research horizons are:

- 5 minutes;
- 15 minutes;
- 30 minutes;
- 60 minutes;
- 240 minutes;
- 720 minutes;
- 1,440 minutes.

`market_snapshots`

Stores the market state attached to candidate events so later analysis can ask not just whether a strategy worked, but **under which market conditions** it worked.

## Strategy A — Wallet convergence

Internal name:

`wallet_convergence_v2`

Purpose: identify multiple independent observed wallets accumulating the same non-base token within a short period.

The engine ignores common base/quote assets:

- wrapped SOL;
- USDC;
- USDT.

Current research logic:

- 30-minute wallet window;
- at least 2 distinct buying wallets -> `observe` candidate;
- at least 3 distinct buying wallets -> trade-grade candidate;
- score rises with independent wallet count and repeated positive events;
- duplicate strategy/mint/tier events are suppressed during the cooldown.

Why keep the two-wallet observations?

Because the final optimum may not be “3 wallets in 30 minutes.” Forward data might show that, for example, two wallets in 5 minutes outperforms four wallets over 30 minutes. The platform is designed to discover that empirically.

## Strategy B — Order-flow acceleration

Internal name:

`order_flow_acceleration_v1`

Purpose: identify tokens where sampled on-chain buying is becoming increasingly one-sided before the move is exhausted.

Token amounts are not compared directly across different assets because one token unit can represent radically different economic value. The first implementation therefore emphasises event counts and wallet breadth.

Current features include:

- positive token events in the most recent 15 minutes;
- negative token events in the most recent 15 minutes;
- buying activity in the preceding 15-minute block;
- distinct buying wallets over 30 minutes;
- buy-event ratio;
- buy-event acceleration versus the previous window.

Current observation threshold:

- at least 2 recent positive events;
- at least 2 distinct buying wallets;
- buy-event ratio >= 60%.

Current trade-grade threshold:

- at least 3 recent positive events;
- buy-event ratio >= 70%;
- buy acceleration >= 1.5x;
- at least 2 distinct buying wallets.

These are starting hypotheses, not sacred parameters. The forward-test dataset exists specifically so they can later be replaced by evidence.

## Strategy C — Liquidity-shock reversal

Internal name:

`liquidity_shock_reversal_v1`

Purpose: test whether sharp short-term downward dislocations in sufficiently liquid trending pools mean-revert when buy participation is already returning.

Unlike Bots A and B, this strategy scans GeckoTerminal's Solana trending-pool universe directly.

Observation threshold:

- 5-minute price change <= -5%;
- liquidity >= $50,000;
- DEX 5-minute buy ratio >= 52%.

Trade-grade threshold:

- 5-minute price change <= -8%;
- liquidity >= $100,000;
- DEX 5-minute buy ratio >= 58%;
- 1-hour change > -25% to avoid blindly buying obvious collapse regimes.

The intention is **not** “buy anything that fell.” It is to isolate severe but potentially temporary price pressure in markets that still have enough liquidity and returning demand to make a rebound trade plausible.

## Strategy D — Volume-confirmed momentum

Internal name:

`volume_momentum_v1`

Purpose: identify short-term continuation where price, turnover, liquidity and buy-side participation agree.

It also scans the independent trending-pool universe.

Observation threshold:

- 5-minute price change >= +1%;
- 1-hour price change >= +2%;
- liquidity >= $50,000;
- 5-minute volume / liquidity >= 1%;
- 5-minute DEX buy ratio >= 55%.

Trade-grade threshold:

- 5-minute price change >= +3%;
- 1-hour price change >= +5%;
- liquidity >= $100,000;
- 5-minute volume / liquidity >= 2%;
- 5-minute DEX buy ratio >= 60%.

The key distinction from naïve momentum is that price movement alone is insufficient. The move must have turnover, adequate executable liquidity and buy-side confirmation.

## Candidate tiers

Every research event has a tier.

### `observe`

Interesting enough to preserve for later analysis, but not strong enough to count as a paper trade under the current rules.

### `trade`

Meets the current paper-entry criteria.

A candidate only receives `shadow_trade=true` if a contemporaneous USD entry price is available. This prevents later price backfilling from quietly giving the strategy an entry it could not have observed at the time.

## Paper/shadow execution assumptions

The v1 research engine treats trade-grade candidates as prospective long entries.

No blockchain order is sent.

At candidate creation the system stores the current USD market reference price. Later the evaluator requests a fresh price and calculates:

```text
raw return % = (future price / entry price - 1) * 100
net return % = raw return % - assumed round-trip friction
```

Current multi-strategy friction assumption:

**80 basis points round trip**

This is intentionally conservative for screening and is not claimed to be the exact execution cost of every future trade.

The original convergence evaluator uses 60 bps and is retained for continuity with the earlier experiment.

## Scoreboard

`research_scoreboard()` groups realised research outcomes by strategy, candidate tier and horizon.

It currently reports:

- sample count;
- average net return;
- median net return;
- win rate;
- worst net return;
- best net return;
- profit factor where defined.

The scoreboard only becomes meaningful as samples accumulate. A handful of winners is not evidence of a durable edge.

Future analysis should also add:

- maximum drawdown of a sequential paper portfolio;
- return distribution / tail loss;
- performance by liquidity bucket;
- performance by market-cap bucket;
- performance by token age;
- performance by DEX;
- time-of-day effects;
- strategy correlation;
- slippage sensitivity;
- rolling / regime stability.

## Legacy convergence engine

`signals.py` contains the original `wallet_convergence_v1` signal engine.

It remains running while the v2 research framework accumulates data. Its current trigger is 3 distinct wallets acquiring the same non-base mint within 30 minutes. New legacy signals now capture a contemporaneous reference price at signal creation. Early pre-v1 legacy outcome rows created before that fix should not be treated as research-grade evidence; the multi-strategy `research_*` tables are the canonical v1 forward-test dataset.

This lets the project retain continuity with the original experiment while the richer candidate framework is tested in parallel.

## Background loops

The FastAPI process launches several asynchronous loops at startup.

### RPC heartbeat

Runs roughly once per minute and records the latest Solana slot.

### Jupiter collector

Runs roughly once per minute and samples recent unprocessed Jupiter transactions.

### Legacy signal scanner

Runs roughly every two minutes.

### Research strategy loop

Starts after the initial warm-up and then runs roughly once per minute.

It evaluates Bots A-D and records any new observation/trade candidates.

### Outcome evaluator

Runs roughly once per minute and records any signal/research outcomes whose measurement horizons have become due.

### Monitoring loop

Checks component freshness, RPC/DB state and budget pressure. Telegram alerts are optional.

## HTTP API

The app binds to port 8000 inside Docker and is exposed only on VPS loopback by default:

`127.0.0.1:8000:8000`

### Health / operations

`GET /health`

Compact component health state.

`GET /status`

Full in-memory state plus DB counts, RPC budget and strategy scoreboard.

`GET /monitoring`

Operational monitoring snapshot and active alerts.

`GET /budget`

Current estimated Helius usage against daily/monthly limits.

`GET /dashboard`

Minimal auto-refreshing browser dashboard.

### Wallet / legacy signals

`GET /wallets/recent`

`GET /signals/recent`

`GET /outcomes/recent`

`GET /outcomes/summary`

### Research platform

`POST /research/run-once`

Runs all current research strategies immediately. Useful for testing; the background loop normally handles this automatically.

`GET /research/candidates?limit=50`

Returns recent observation and trade candidates.

`GET /research/candidates?limit=50&shadow_only=true`

Returns only candidates that qualified as prospective paper trades.

`GET /research/scoreboard`

Returns research counts and strategy/horizon performance.

`POST /outcomes/run-once`

Forces both the legacy and multi-strategy evaluators to check for due measurements.

## RPC budget control

`budget.py` prevents the experiment silently consuming unlimited Helius credits.

Defaults:

```text
DAILY_CREDIT_BUDGET=32000
MONTHLY_CREDIT_BUDGET=900000
```

The monthly default intentionally leaves headroom below a nominal one-million-credit allocation.

Before normal RPC calls are made, estimated usage is checked against the configured limits. If the next call would exceed a hard budget, the call is rejected.

## Configuration

Copy `.env.example` to `.env` and set secrets locally on the server.

Required values:

```dotenv
APP_ENV=production
PAPER_TRADING_ONLY=true
HELIUS_API_KEY=replace_me
POSTGRES_PASSWORD=replace_with_a_long_random_password
```

Optional monitoring:

```dotenv
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Never commit `.env`.

## Running locally / on a VPS

With Docker and Docker Compose installed:

```bash
docker compose up -d --build
```

Check containers:

```bash
docker compose ps
```

Check health:

```bash
curl http://127.0.0.1:8000/health
```

Inspect status:

```bash
curl http://127.0.0.1:8000/status
```

Inspect research candidates:

```bash
curl 'http://127.0.0.1:8000/research/candidates?limit=20'
```

Inspect the scoreboard:

```bash
curl http://127.0.0.1:8000/research/scoreboard
```

Logs:

```bash
docker compose logs -f app
```

## Deployment

The repository contains `.github/workflows/deploy.yml`.

Pushes to `main` trigger the GitHub Actions deployment workflow. The workflow SSHes to the VPS and runs:

```bash
cd /home/deploy/venture-lab && bash deploy.sh
```

The GitHub repository therefore acts as the source-of-truth code history while PostgreSQL on the VPS holds the live research dataset.

Required GitHub Actions secrets are:

- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`

## Repository files

`app.py` — FastAPI service, state, loops and HTTP endpoints.

`collector.py` — Jupiter transaction sampler and Solana transaction normalisation.

`db.py` — original/core PostgreSQL schema and helpers.

`research_db.py` — v1 multi-strategy research schema, candidate/outcome persistence and scoreboard.

`signals.py` — original wallet convergence strategy.

`research.py` — Bots A-D and research-cycle orchestration.

`marketdata.py` — GeckoTerminal token/trending-pool market adapter.

`evaluator.py` — prospective forward outcome measurement for legacy signals and research candidates.

`budget.py` — Helius credit accounting and hard budget limits.

`monitoring.py` — component-age checks and optional Telegram alerts.

`docker-compose.yml` — PostgreSQL + application services.

`Dockerfile` — Python application image.

`deploy.sh` — VPS deployment script used by GitHub Actions.

`.github/workflows/deploy.yml` — push-to-main deployment workflow.

## Why multiple specialist bots?

The working thesis is that crypto does not have one universal microstructure regime.

Different assets and circumstances may reward different behaviours:

- wallet clustering can reveal coordinated/informed accumulation;
- persistent order flow can precede continuation;
- temporary liquidity shocks can mean-revert;
- liquid high-turnover assets can exhibit momentum;
- future bots may exploit leader/laggard propagation or derivatives crowding.

A portfolio of genuinely different edges is more attractive than six cosmetic variations of one momentum rule.

The platform therefore separates:

1. data collection;
2. feature generation;
3. strategy hypotheses;
4. prospective candidate recording;
5. outcome evaluation;
6. eventual portfolio allocation.

That separation is deliberate: strategy code should say **“I have a hypothesis.”** A future portfolio manager should decide **“does this deserve capital?”**

## Research rationale / literature starting points

The project is inspired by several documented effects rather than by a claim that any paper can be copied directly into a profitable bot.

Useful research directions include:

- order-flow predictability and the distinction between temporary price pressure and persistent information;
- short-term reversal / liquidity provision in less-liquid crypto markets;
- volume-confirmed time-series momentum;
- cross-cryptocurrency lead/lag predictability;
- on-chain flow information;
- perpetual-futures funding, basis and crowding.

Examples used during strategy design include:

- *Order Flow and Cryptocurrency Returns*, Journal of Financial Markets (2026): https://doi.org/10.1016/j.finmar.2026.101047
- crypto short-term reversal/liquidity literature: https://www.sciencedirect.com/science/article/pii/S0378426622001418
- cross-cryptocurrency return predictability: https://www.sciencedirect.com/science/article/pii/S0165188924000551
- on-chain flow forecasting study: https://arxiv.org/abs/2411.06327

These references motivate hypotheses only. Venture Lab's own prospective data decides whether a strategy survives.

## Planned Bot E — Leader / laggard propagation

Future hypothesis:

Learn rolling relationships such as:

```text
leader move -> laggard response after 5m / 15m / 1h / 4h
```

Potential clusters could include major asset -> ecosystem token or sector leader -> smaller sector member.

This bot should be built only after the shared multi-asset history is deep enough to test relationships out of sample.

## Planned Bot F — Perpetual futures / crowding

Future data may include:

- funding rates;
- basis;
- open interest;
- liquidations;
- spot/perp divergence;
- crowding measures.

Possible modes are market-neutral carry and directional crowding reversal. This requires a separate derivatives data integration and is intentionally not part of the first spot research build.

## Future portfolio manager

The eventual design should keep signal generation separate from capital allocation.

A future allocation layer can consider:

```text
expected edge
x strategy confidence
x historical reliability in the current regime
x liquidity/execution quality
x portfolio diversification
x current exposure / drawdown constraints
```

If two genuinely independent strategies identify the same asset at the same time, the portfolio manager can treat agreement as information. If strategies conflict, it can reduce or reject exposure.

## What must be proven before live trading

No strategy should graduate because of one impressive winner.

At minimum, evaluate:

- a meaningful number of prospective samples;
- average **and median** returns;
- realistic net returns after friction;
- profit factor;
- win/loss asymmetry;
- tail losses;
- sequential drawdown;
- regime stability;
- liquidity and market-cap dependence;
- whether performance survives stricter slippage assumptions;
- whether a few extreme winners explain the entire result;
- whether results remain positive after thresholds are frozen.

A reasonable initial research target is approximately 100-200 prospective trade-grade samples per strategy/variant before making strong claims, while obviously bad strategies can be rejected much sooner.

## Current status

The platform is live in shadow mode on the VPS.

As of the v1 multi-strategy deployment:

- Solana RPC heartbeat is operating;
- PostgreSQL is persistent and healthy;
- Jupiter sampling is operating continuously;
- the original convergence scanner remains active;
- Bots A-D are implemented;
- sub-threshold observation candidates are retained;
- trade-grade candidates receive contemporaneous paper entry prices;
- forward outcomes are evaluated automatically;
- a common strategy/horizon scoreboard is available;
- no real-money execution path exists.

The first live v1 research cycle successfully produced both an observation candidate and a trade-grade momentum shadow entry, confirming that the complete candidate -> entry -> future-outcome pipeline is active.

## Philosophy

This repository is an experiment, not a promise of returns.

The useful outcome may be a profitable strategy, a collection of weak effects that combine into something useful, or a clear demonstration that a hypothesis does not survive real costs and forward testing.

All three are valid research results.

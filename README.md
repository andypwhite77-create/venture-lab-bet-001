# Venture Lab Bet 001 — Multi-Strategy Solana Research Engine

Venture Lab Bet 001 is a live-market, **paper/shadow-trading research platform** for testing whether public Solana activity contains repeatable trading edges after realistic friction.

It began as a single wallet-convergence experiment and now runs four distinct strategy families against shared blockchain and market data. The system records both trade-grade signals and sub-threshold observations, measures forward returns at fixed horizons, and maintains a common scoreboard so strategies can be compared without changing the rules after the fact.

The project is intentionally research-first. The main research application remains paper/shadow-only and refuses to start unless `PAPER_TRADING_ONLY=true`. A separate isolated Reversal Canary execution path exists behind deterministic risk limits, an end-to-end dry-run gate, and an explicit human arm action; research/Queen processes do not receive signer authority.

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
PUBLIC LIVE DATA -> SHARED DATA LAYER -> STRATEGY ENGINE -> research_candidates -> FORWARD EVALUATOR -> research_outcomes -> SCOREBOARD
```

### Current evolutionary platform — 2 October 2026

The research platform has expanded beyond the original four fixed strategy engines. The current hierarchy is **Swarm Queen → deterministic Breeding Queen → specialist ant populations**, with Spartan v2 acting as an external adversarial examiner. The active general-Queen methodology is `queen-v8-directed-mutation-credit`: parent→child train/validation deltas teach the breeder whether local, standard or wide mutation is currently producing stronger descendants, while every operator keeps a mandatory exploration floor. Sealed holdout and Spartan answers never feed this mutation credit.

Reversal runs a bounded continuous-v2 prospective lineage; failed but informative Spartan finalists can enter a quarantined paper-only Alumni breeding pool; and a permanent Hall of Fame stores up to three behaviourally distinct top performers from every completed Spartan exam. Alumni/Hall-of-Fame ancestry inherits genetics only, never validation credit. Real-money execution authority remains a separate deterministic/human gate; the presence of canary execution infrastructure does not imply that live trading is enabled.

See `docs/QUEEN_ARCHITECTURE.md`, `docs/grace-colony-architecture.md`, `docs/grace-evolutionary-trading-swarm.md`, and `docs/SPARTAN_V2.md` for the current platform model.

### Champion Canary merit roster — 8 October 2026

The Canary signal source is a fixed Champion roster (default five seats), not the full Reversal research population. Research challengers earn a roster seat only after at least 25 fresh paper trades across three days and must satisfy reliability gates for win rate, median return, positive-day rate and worst loss while beating the weakest incumbent on forward, historical Arena and combined Champion scores. One roster seat may rotate per five-minute maintenance tick.

Canary intents persist individual voter attribution in `canary_intent_votes`, making future per-ant Canary qualification measurable. The intended next rung is to require a meaningful attributable Canary sample (target roughly 25 Canary trades) before live-pool eligibility; that second automatic promotion is not implemented yet. Global live authority remains human-controlled.

Breeding Queen campaign handoff is now five behaviour-distinct finalists rather than two. Search volume remains two 10,000-genome waves followed by the restart-safe 24-hour cooldown, and no Champion/Canary/Spartan evidence gate was weakened.

## Safety / research guardrails

The current build has deliberately hard boundaries:

- the main research application is paper/shadow-only;
- Queen/research services receive no private keys or signer credentials;
- the isolated Canary signer path is disabled unless explicitly human-armed after a successful genuine future dry run;
- no leverage or borrowing;
- £1 Canary max trade, 0.003 SOL network/exit reserve, fixed Champion Canary roster, one-position maximum and fail-closed reconciliation;
- conservative assumed round-trip friction on research trades;
- RPC credit budgets with hard stops;
- candidate deduplication/cooldowns;
- forward outcomes are measured after the event rather than retroactively selecting good historical examples.

`app.py` aborts startup if `PAPER_TRADING_ONLY` is not `true`.

## Data sources

### Helius Solana RPC

Helius supplies Solana RPC data. The collector samples recent Jupiter v6 activity rather than trying to index the entire chain. The build uses `getSlot`, `getSignaturesForAddress`, and `getTransaction`. RPC use is metered internally in `budget.py`.

### Jupiter activity

`collector.py` samples transactions involving the Jupiter v6 program `JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4`. Each sampled transaction is normalised into signature, slot, block time, signer wallet, source program, fee, success/failure, native SOL delta, signer-owned token deltas and lightweight transaction metadata. Versioned transactions are supported through `maxSupportedTransactionVersion: 1`.

### GeckoTerminal

GeckoTerminal supplies public market information without trading credentials. Multi-token snapshots provide contemporaneous USD prices for wallet/flow candidates, while Solana trending-pool data drives reversal and momentum research. The adapter uses retry/backoff and batches multi-token requests.

## Database

PostgreSQL 16 runs in Docker with a persistent named volume.

Core tables include `rpc_samples`, `wallets`, `observed_transactions`, `signal_events`, `signal_outcomes`, `paper_trades`, `engine_events`, and `rpc_usage`.

Research tables:

- `research_candidates`: all candidate events, including observe and trade tiers, with score, contemporaneous entry price, friction assumption, feature JSON and market JSON.
- `research_outcomes`: prospective forward performance on the canonical horizon grid plus exact, prospectively requested horizons used by Spartan Alumni hold-time exploration. Bespoke horizons are requested before maturity; historical prices are never fabricated after the fact.
- `market_snapshots`: market state attached to candidate events.
- `research_price_path`: minute-by-minute forward price observations for active trade-grade shadow candidates during their first four hours, enabling later stop-loss, take-profit, trailing-exit, maximum favourable excursion and maximum adverse excursion research.

## Strategy A — Wallet convergence

Internal name: `wallet_convergence_v2`.

Purpose: identify multiple independent observed wallets accumulating the same non-base token within a short period. Wrapped SOL, USDC and USDT are ignored. Current logic observes at 2 distinct buying wallets in 30 minutes and marks trade-grade at 3 or more. These are starting hypotheses rather than sacred parameters.

## Strategy B — Order-flow acceleration

Internal name: `order_flow_acceleration_v1`.

Purpose: identify tokens where sampled on-chain buying is becoming increasingly one-sided. Features include positive/negative events, previous-window activity, distinct buying wallets, buy-event ratio and acceleration. The current observe threshold requires at least 2 recent positive events, 2 buying wallets and a 60% buy-event ratio. Trade-grade requires at least 3 positives, 70% buy ratio and 1.5x acceleration.

## Strategy C — Liquidity-shock reversal

Internal name: `liquidity_shock_reversal_v1`.

Purpose: test whether sharp short-term downward dislocations in sufficiently liquid trending pools mean-revert when buy participation is already returning.

Observe: 5-minute change <= -5%, liquidity >= $50k, 5-minute buy ratio >= 52%.

Trade-grade: 5-minute change <= -8%, liquidity >= $100k, buy ratio >= 58%, and 1-hour change > -25%.

## Strategy D — Volume-confirmed momentum

Internal name: `volume_momentum_v1`.

Purpose: identify continuation where price, turnover, liquidity and buy-side participation agree.

Observe: 5-minute change >= +1%, 1-hour >= +2%, liquidity >= $50k, 5-minute volume/liquidity >= 1%, buy ratio >= 55%.

Trade-grade: 5-minute change >= +3%, 1-hour >= +5%, liquidity >= $100k, 5-minute volume/liquidity >= 2%, buy ratio >= 60%.

## Candidate tiers

`observe` means interesting enough to retain for later analysis. `trade` means it meets current paper-entry criteria. A candidate only receives `shadow_trade=true` if a contemporaneous USD entry price exists; future backfilling is not used to invent entries.

## Paper/shadow execution assumptions

All current multi-strategy entries are prospective longs. No blockchain order is sent. Raw return is future price divided by entry price minus one. The current research friction assumption is 80 basis points round trip. The original convergence evaluator retains 60 bps for continuity.

## Scoreboard

The scoreboard groups realised outcomes by strategy, candidate tier and horizon and reports sample count, average and median net return, win rate, worst/best return and profit factor. It should not be interpreted as reliable from a handful of samples. Planned analysis includes drawdown, tail loss, liquidity/market-cap/token-age/DEX buckets, time-of-day effects, correlation, slippage sensitivity and rolling regime stability.

## Background loops

- RPC heartbeat: about once per minute.
- Jupiter collector: about once per minute.
- Legacy convergence scanner: about every two minutes.
- Research strategy loop: about once per minute.
- Outcome evaluator: about once per minute.
- Trade path sampler: about once per minute for the first four hours of active shadow trades.
- Monitoring loop: component freshness, budget pressure and optional Telegram alerts.

## HTTP API

The app binds to port 8000 inside Docker and is exposed on VPS loopback by default.

Key endpoints:

- `GET /health`
- `GET /status`
- `GET /monitoring`
- `GET /budget`
- `GET /dashboard`
- `GET /wallets/recent`
- `GET /signals/recent`
- `GET /outcomes/recent`
- `GET /outcomes/summary`
- `POST /research/run-once`
- `GET /research/candidates?limit=50`
- `GET /research/candidates?limit=50&shadow_only=true`
- `GET /research/scoreboard`
- `POST /outcomes/run-once`
- `POST /research/sample-paths`

## RPC budget control

`budget.py` prevents unlimited Helius use. Defaults are `DAILY_CREDIT_BUDGET=32000` and `MONTHLY_CREDIT_BUDGET=900000`. Calls are checked before execution and hard-stopped at the configured budget.

## Configuration

Required values in `.env`: `APP_ENV=production`, `PAPER_TRADING_ONLY=true`, `HELIUS_API_KEY`, and `POSTGRES_PASSWORD`. Optional Telegram settings are `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Never commit `.env`.

## Running / deployment

Run with `docker compose up -d --build`. Health is available at `curl http://127.0.0.1:8000/health`; research status at `/status` and `/research/scoreboard`.

Pushes to `main` use `.github/workflows/deploy.yml`, which SSHes to the VPS and runs `/home/deploy/venture-lab/deploy.sh`. Required GitHub Actions secrets are `VPS_HOST`, `VPS_USER`, and `VPS_SSH_KEY`.

## Repository files

- `app.py`: FastAPI service, loops and endpoints.
- `collector.py`: Jupiter transaction sampler.
- `db.py`: core PostgreSQL schema/helpers.
- `research_db.py`: multi-strategy research persistence and scoreboard.
- `signals.py`: original wallet convergence strategy.
- `research.py`: Bots A-D.
- `marketdata.py`: GeckoTerminal adapter with retry/backoff and batching.
- `path_sampler.py`: minute-level price-path collection.
- `evaluator.py`: prospective outcome measurement.
- `budget.py`: Helius credit accounting/hard limits.
- `monitoring.py`: component freshness and optional alerts.
- `docker-compose.yml`, `Dockerfile`, `deploy.sh`: deployment/runtime.

## Why multiple specialist bots?

Crypto does not appear to have one universal microstructure regime. Wallet clustering, order flow, temporary liquidity shocks and liquid-asset momentum are distinct hypotheses. Future bots may target leader/laggard propagation or derivatives crowding. Signal generation remains separate from eventual capital allocation.

## Research rationale / literature starting points

Strategy design was motivated by documented effects rather than by a claim that papers can be copied directly into profit. Useful starting points include order-flow predictability, short-term reversal/liquidity provision, volume-confirmed momentum, cross-crypto lead/lag, on-chain flows and perpetual futures crowding. Examples include *Order Flow and Cryptocurrency Returns* (Journal of Financial Markets, 2026), crypto reversal/liquidity literature, cross-crypto return predictability research and on-chain flow forecasting work.

## Planned Bot E — Leader / laggard propagation

Future hypothesis: learn rolling `leader move -> laggard response` relationships at 5m, 15m, 1h and 4h. Build only after enough shared multi-asset history exists for out-of-sample testing.

## Planned Bot F — Perpetual futures / crowding

Future inputs may include funding, basis, open interest, liquidations, spot/perp divergence and crowding. Potential modes are market-neutral carry and directional crowding reversal.

## Future portfolio manager

The eventual allocation layer should combine expected edge, confidence, regime reliability, execution quality, diversification and current exposure/drawdown constraints. Agreement between genuinely independent strategies can be treated as information; conflicting strategies can reduce or reject exposure.

## What must be proven before live trading

No strategy graduates because of one winner. Evaluate meaningful prospective sample size, mean and median return, net performance after friction, profit factor, win/loss asymmetry, tail losses, sequential drawdown, regime stability, liquidity/market-cap dependence, slippage sensitivity, concentration in extreme winners and performance after thresholds are frozen. Roughly 100–200 prospective trade-grade samples per strategy/variant is a sensible initial target before strong claims, while obviously bad ideas can be rejected sooner.

## Current status

The platform is live in shadow mode on the VPS. RPC, PostgreSQL, Jupiter sampling, legacy convergence, Bots A-D, candidate logging, prospective pricing, outcome evaluation, price-path sampling and common scoreboards are active. A separate bounded Reversal Canary execution path exists but remains human-gated; Elite/Queen status cannot grant transaction authority.

## Philosophy

This repository is an experiment, not a promise of returns. A profitable strategy, a collection of weak effects that combine usefully, or a clear demonstration that a hypothesis fails after costs are all valid research outcomes.

## Evolutionary acceleration and elite-only training (28 Sep 2026)

The colony now separates cheap historical search from expensive prospective evidence. Each bloodline can breed and replay roughly 10,000 broad genomes against stored observations, then run a second elite-directed search around promising parameter regions. Historical data is split chronologically into train, validation and an untouched holdout audit. Historical performance can nominate a genome for prospective life, but never counts as prospective proof.

Four independent 100-ant tournaments exist for reversal, momentum, order flow and wallet convergence. Their nominal elimination ladder is `100 -> 60 -> 30 -> 15 -> 5 -> frozen holdout`, with one immortal founder baseline per bloodline. However, active prospective slots are now reserved for the frozen control plus genomes that have already passed the historical walk-forward and holdout gates. Broad/random nursery organisms remain archived but do not consume new forward observations.

Continuous evolution is asynchronous. Clearly failed prospective elites can be retired early; vacant slots are replenished from a queue of historically qualified candidates and every replacement starts prospective evidence from zero. This prevents weak/random ants from consuming scarce future information merely because they were born into the current population.

The accelerator reruns only after at least 25 genuinely new independent mints have accumulated, rather than repeatedly mining an unchanged dataset. It also searches regime specialists and runs generic feature-pattern discovery across multiple horizons. Pattern discovery is allowed to return no robust strategy; failure to find an out-of-sample edge is treated as useful evidence rather than a reason to lower standards.

A feature-definition fault was also corrected in wallet convergence: `flow_ratio_15` is a buy-share bounded to `[0,1]`, so the former `>=1.2` threshold was impossible. The corrected founder equivalent is approximately `0.545455` (the buy share corresponding to a 1.2 buy:sell ratio). Existing contaminated evidence is not silently rewritten; repaired experiments are versioned separately.

## Elite prospective roster and challenger queue

Prospective training capacity is now treated as scarce. Each bloodline keeps its frozen founder/control active, while non-control prospective slots are reserved for genomes that passed historical walk-forward screening and an untouched holdout audit. Broad/random nursery organisms remain archived but do not consume new market observations.

Qualified genomes that cannot immediately enter an active roster remain in a ranked challenger queue ordered by historical screening score. A challenger cannot displace an incumbent on backtest strength alone. Turnover requires the incumbent to have at least 12 independent prospective mints, a non-positive prospective tournament score, and the challenger to have a materially stronger historical admission score (at least +0.01 or +15%, whichever is larger). The founder/control is never replaceable.

A displaced incumbent retains its full prospective evidence and elimination reason. An incoming challenger begins with zero prospective credit. This creates persistent competitive pressure without letting retrospective optimisation rewrite forward evidence.

## £25 stake economics (2026-09-28)

Paper economics now use a £25 per-ant reference stake, matching the intended tiny live-canary scale. Fixed execution costs are modelled separately from percentage edge so a strong signal is not rejected merely because an unrealistically tiny paper stake makes fixed fees dominate. Recent observed successful Jupiter transaction fees provide the fixed network-cost estimate; proportional friction remains separate. The engine records net £ economics and an implied break-even stake while preserving the underlying percentage-return signal.

The £25 execution-reality probe is prospective-only and begins after candidate 1395. It uses read-only Jupiter quotes and never signs or broadcasts. Historical evidence still cannot substitute for prospective proof, and live authority remains disabled.

## Breed, test, take the best

The governing evolutionary rule is simple: breed descendants, test them prospectively on independent opportunities, and retain only the strongest evidence-backed performers. Paper evidence is cheap, so selection must favour proof over speed.

Reversal uses increasingly demanding cumulative gates: 20 independent mints before 100→60, 40 before 60→30, 60 before 30→15, and 80 before 15→5. The final five are then frozen and must survive 50 entirely new independent mints. Historical/backtest strength cannot substitute for prospective evidence.

Children are judged primarily against the bloodline and also against their parent window. Weak parents must produce genuine improvement. Elite parents may produce descendants that preserve strong expectancy while improving robustness, tail behaviour, drawdown, execution quality, or regime coverage. No descendant advances merely because it is less bad than a weak parent.

Selection rewards net expectancy after costs, control/baseline edge, consistency and robustness, while penalising tail loss, drawdown, outlier/moonshot dependence and excessive correlation with stronger relatives. Failed descendants are archived/demoted; they do not receive live capital. Live-ready remains eligibility only and cannot grant itself execution authority.

### Deep historical breeding and fast prospective admission

Reversal now uses a compute-heavy historical funnel: each acceleration cycle breeds 50,000 candidate genomes, scores them chronologically on train/validation data, and uses an untouched historical holdout only as a veto. Only the top 10 robust/diverse survivors are admitted to prospective live-market paper observation. Historical performance never counts as prospective proof.

The prospective admission rule is deliberately short but strict: after at least 20 independent future mints, candidates must have positive mean and median net return, positive matched edge versus the immortal Reversal control, and no catastrophic-tail trigger. Correlation-adjusted ranking then admits at most the top five to `colony_genomes` with `status=production`. Existing parents remain in the population; promotion adds children rather than replacing parental genetic memory. Production status is live-ready/main-pool membership only and does not grant real-money transaction authority.

A separate `historical-bank` service continuously archives hourly GeckoTerminal OHLCV for every observed Solana pair, backfilling up to roughly six months where the public endpoint provides it. Existing candidate features, outcomes, minute price paths and market snapshots continue to accumulate prospectively, so the local research bank becomes deeper with time.

### Multi-colony swarm
The four strategy families now operate as isolated evolutionary colonies over a shared evidence bank. Dashboard tabs expose Swarm, Reversal, Momentum, Order Flow, and Wallet Convergence independently. Each Queen owns only its family's genetics and tournament state; market data can be shared because different strategies may take different decisions on the same mint. Fresh-evidence accelerator sweeps now test 50,000 genomes per family and admit only historically qualified finalists to prospective testing.


## 2 October 2026 late hardening and governance update

- Champion/Challenger League added five founding Reversal Elite behaviours, a cumulative append-only Qualification corpus, and an admin Elite control plane. League status and requested capital mode do not grant signer authority.
- Queen roles were split: the Breeding Queen owns bounded genome creation/evolution, while the Swarm Queen is a research director that can diagnose regimes and allocate research attention but cannot mutate genomes, promote candidates, change Spartan gates, trade, or sign.
- Breeding Queen precision cadence is 10,000 genomes per wave, two waves per campaign, followed by cooldown/review; quality is preferred over forced throughput.
- Admin password recovery was added with short-lived single-use recovery tokens, session invalidation, and Safari UI compatibility fixes.
- Spartan Alumni now retain exact arbitrary hold durations from 3 to 240 minutes. A dedicated hold-probe lane tests timing independently (for example 3/4/6/8/15/30 minutes) and requests exact prospective outcomes dynamically.
- Dynamic outcome requests are stored in `research_outcome_requests`; SQL parameter typing is explicit to avoid asyncpg ambiguity. No historical outcome is backfilled simply because a new horizon is requested.
- Canary controller pagination now excludes already-seen intents before applying its page limit, preventing a healthy-looking controller from starving on an old first page.
- Canary execution sizing is repriced at fresh SOL/GBP FX at execution time and can only shrink from the intent amount, preventing harmless FX movement from tripping or exceeding the £1 cap.
- Canary dry-run remains mandatory: a genuine future >=80% Reversal intent must be claimed, quoted, simulated through the original hold, exited, and persisted closed before `canary-arm` can succeed.

### Canary dry-run milestone

The first qualifying end-to-end Reversal Canary dry run completed on 2 October 2026. A genuine future 100%-consensus signal was claimed fresh, quoted through Jupiter, simulated for its original five-minute hold, quoted for exit and persisted closed with `broadcast=false`. The arm gate is therefore satisfied, but the Canary remains stopped/disarmed until a human explicitly invokes `scripts/canary-arm`.

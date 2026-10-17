# Venture Lab: systems audit — 17 October 2026

This document reports observed code paths and live-state checks, not a certification of safe or profitable live trading.

## Verified runtime and boundaries

- Seventeen Docker Compose services running at audit; app, admin, PostgreSQL and Canary executor reported healthy.
- Canary control `armed=false`, `stopped=true`; no change to live authority.
- Four quote-to-quote review rows and zero qualifying Hall-of-Fame passes observed.
- Queen Treasury USD resource-cost table has no rows. Zero recorded dollars is **unknown cost**, not free computing.

## Priority P0 — Qualification cohort mismatch

`colony/queen_survival_loop.py` checks freshly examined Spartan finalist IDs against `quote_to_quote_ledger.run()` and `quote_survival_gate.verdict()`. The ledger only reads `eve_reference_paper_entries` tied to `controlled_paper_cohort.status='observation_only'`, restricted to observations in the last 24 hours. There is no verified automatic path enrolling newly selected finalist genomes into those observation cohorts. Thus a new finalist may have no qualifying quote history even if it passed Spartan. **Fail closed for advancement**, but create an explicit prospective probation/enrolment path, with a new clock and immutable genome ID, rather than counting absence as trading failure.

## Priority P0 — Ledger missing-exit accounting

`colony/quote_to_quote_ledger.py` correctly reserves 0.01 SOL for an entered position whose exit quote is missing, but unresolved exposure can accumulate and starve the simulated bankroll. Add expiry, observation health, optional later-exit research marked as delayed (never a contemporaneous fill), and a reasoned intervention queue. Do not backfill fictitious exits. Quoted returns are not fills.

## Priority P1 — Pricing and execution

- GeckoTerminal/DexScreener archived price observations lack provider-origin timestamps in the sampled six-hour audit. Collection-time freshness is not provider tick freshness. The archived entry fallback now rejects missing origin timestamps.
- Jupiter quotes are sized route evidence; available liquidity, congestion, quote expiry, priority fees and realized execution prices still need independent testing.
- Jupiter quote backoff is per process, not a cross-container rate budget. Track 429 coverage separately for each observer, quote priority and endpoint.
- ETH five-minute Kraken OHLC paper entries are price-reference marks, not executable bid/ask fills.
- The hard 25-pair threshold is merely a screening minimum; qualification also requires diverse days/regimes and out-of-sample results.

## Priority P1 — Economic selection

Treasury costs are not yet populated. CPU snapshots do not determine billed hosting, API or model inference costs. Require measured expenditure and compare challenger-minus-baseline return before increasing resources.

## Priority P2 — Operational resilience

Audit restart idempotence, durable logs, cron overlap, queue starvation, metrics staleness, backup restoration, and sandbox-vs-production secrets. Inject transport errors, API 429s, missing quote data and duplicate rows into tests.

## Later runtime findings (17 October)

- ETH evolutionary paper database: 112 closed observations across six seeded genomes, combined mark P/L -$11.4628. Two genomes retired after 25 losing marks; four are still gathering observations. Sum of independent paper arms is not a real wallet loss.
- Recent GeckoTerminal requests frequently hit a provider cooldown; DexScreener supplies much of the fallback. Cycle coverage near 100% must not be reported as independent-source redundancy or verified quote executability.
- `queen_survival_loop.py` currently reports quote-gate eligibility after Spartan but does not provide a verified automatic enrolment path to collect prospective quotes for those new finalist genome IDs. Treat the gate as a fail-closed diagnostic until the pipeline is completed, not proof that candidate promotion is end-to-end functional.
- `quote_to_quote_ledger.py` looks back only 24 hours when reconstructing simulated book cash. Thus its reported balance is a rolling-window reconstruction, NOT a durable wallet NAV; older exposure can fall out of the window. Move to an append-only event ledger with an initial bankroll and time-consistent liquidation rules before allowing it to govern financial comparisons.

## Recommended sequencing

1. Add an immutable prospective finalist-to-cohort admission process with explicit probation status; never use previously observed outcomes to qualify newly admitted genomes.
2. Add quote-age and incomplete-exit diagnostics without fabricated fills.
3. Add cost metering and report strategy improvement relative to low-cost baselines.
4. Add executable bid/ask tests for ETH and independent forward holdouts.

**Safety boundary:** Research admission is not live promotion. Canary remains disarmed unless separately and explicitly authorized.

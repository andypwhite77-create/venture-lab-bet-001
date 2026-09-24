# Venture Lab Bet 001 — Solana Wallet Signal Engine

Research-first system for testing whether public Solana wallet behaviour contains a repeatable, exploitable signal after realistic costs.

## Guardrails

- Paper trading only by default.
- No wallet private keys required for research mode.
- No leverage or borrowing.
- Secrets live in Railway environment variables, never in this repository.

## Phase 1

1. Verify reliable Solana RPC ingestion.
2. Persist market/wallet observations.
3. Build wallet scoring and signal hypotheses.
4. Backtest with fees/slippage assumptions.
5. Forward paper trade before considering any live execution.

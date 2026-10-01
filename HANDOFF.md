# Venture Lab handoff

Work in `/home/deploy/venture-lab`.

Inspect the existing project before changing anything. Do not redesign Queen, the tournaments, or the database unless required for compatibility.

The immediate task is to finish and harden the Reversal canary execution plumbing around the existing Hummingbot Gateway/Jupiter setup.

Important existing facts:
- Hummingbot Gateway is local on `127.0.0.1:15888`.
- The dedicated Solana canary wallet has already been imported into Gateway.
- Expected public wallet: `j4nCnM29iyZx9n8oKHXBk8HNJESZb5yaBsA1VkvtkGZ`.
- Existing controller: `colony/canary_controller.py`.
- Existing table: `canary_trade_intents`.
- Existing scripts: `scripts/canary-*`.
- Current limits are £1 max trade, £4 wallet floor, >=80% Reversal consensus, one open position maximum, no leverage/margin/borrowing.

Security rules:
- Never print, echo, copy, expose, or log private keys, API keys, bearer tokens, or secret `.env` values.
- Reuse the existing Gateway wallet and environment variables.
- Queen/research code must never receive wallet credentials.

What to inspect first:
- `colony/canary_controller.py`
- `docker-compose.yml`
- `scripts/canary-*`
- current Postgres schema
- installed Gateway OpenAPI/routes

Complete the missing canary executor and reconciliation plumbing using the installed Hummingbot Gateway/Jupiter API. Preserve the existing risk limits and ensure duplicate execution cannot occur after crashes or restarts.

Before any live-capable path is considered complete, prove an end-to-end dry run using a genuine future Reversal intent: claim intent atomically, re-check all limits, obtain a real Jupiter quote, validate route/slippage/price impact, persist the simulated position, handle the planned exit, and reconcile state cleanly.

Add or improve status/stop tooling so the operator can see the canary state and halt it quickly.

Do not expose secrets while debugging.

At the end, report:
1. files changed,
2. tests performed,
3. current safety state,
4. any unresolved issue,
5. exact operator commands for status, stop, and whatever final human-controlled enable step remains.

Do not silently enable live trading while working on this task.

## Continuation state — 2026-10-01

Implemented and deployed the executor and the existing pinned Gateway response-schema
patch. Live execution remains disabled (`canary_control.armed=false`). The controller
still has `CANARY_LIVE_ENABLED=0` and owns no broadcasting authority.

Sixteen tests pass, including isolated real-PostgreSQL concurrency, unique-position
constraint, restart recovery, known-signature reconciliation, uncertain/crashed
submission no-retry, stale-claim rejection, stop boundaries, and dry-run arming gate.
Test rows are confined to temporary schemas and removed after each test.

A real SOL/USDC Jupiter £1 quote passed route/slippage/impact validation after deploying
Dockerfile.gateway. This preflight is NOT the required future Reversal end-to-end proof.
No production transactions were broadcast and no historical intent was replayed.

The executor is observing future genuine controller intents in dry mode. On a qualifying
fresh intent it atomically claims, validates funding/consensus/caps, quotes entry,
persists a simulated position, waits the original hold_minutes, quotes the exit, persists
closed state, and automatically stops/disarms with problem=dry_run_complete.
An error instead stops/disarms for investigation. No synthetic production intent or
shortened production hold is permitted. The outstanding step is observing that genuine
future qualifying Reversal intent and its planned exit; inspect persisted execution
entry_quote, exit_quote, eligible_since, and closed_at before claiming completion.

Operator commands (usable from any directory):
- Status: /home/deploy/venture-lab/scripts/canary-status
- Stop/disarm: /home/deploy/venture-lab/scripts/canary-disarm
- Start/restart future dry observation: /home/deploy/venture-lab/scripts/canary-dry-run
- Human-controlled future live enable: /home/deploy/venture-lab/scripts/canary-arm

Stop/disarm commits stopped=true and armed=false first, then stops the executor service.
It does not liquidate positions. A transaction already past the committed submission
boundary may have been sent; uncertain submissions are retained and NEVER retried.
Arming refuses unresolved positions, requires a completed future dry run, checks wallet
identity and funding/fresh FX, and starts the service. Never run arm while finishing
this handoff: it is the operator's explicit later live-enable action.

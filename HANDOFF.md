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

## Continuation state — 2026-10-02 late update

Recent hardening commits after the earlier recovery snapshot include Champion/Challenger qualification, cumulative Qualification corpus, explicit Queen role separation, Breeding Queen precision cadence, admin password recovery, exact Spartan Alumni hold-time exploration, Canary pagination repair, Canary execution-time FX repricing, and dynamic-outcome SQL typing repair.

Spartan Alumni may explore exact hold times from 3 to 240 minutes. Exact noncanonical horizons are registered prospectively in `research_outcome_requests` and scored only when the requested horizon genuinely matures. A small `hold_probe` lane changes hold time only, preserving entry logic so timing effects can be isolated.

The Canary controller previously starved behind the oldest 50 already-seen Reversal groups. `latest_reversal_groups()` now excludes existing `canary_trade_intents` before `LIMIT`, so the controller remains on the live edge. Execution-time sizing also recalculates the SOL amount against fresh Kraken SOL/GBP and may shrink but never grow beyond the stored intent / £1 cap.

A dynamic-outcome scheduling regression (`asyncpg.exceptions.AmbiguousParameterError`) was fixed by explicitly casting the requested horizon parameter to integer in `request_candidate_outcome()`. Live PostgreSQL validation passed and consecutive Colony cycles completed without traceback.

Current execution rule remains unchanged: do not silently arm live trading. A successful genuine-future dry run must create a closed `mode=dry` intent with persisted entry and exit quotes. Only after `scripts/canary-status` shows that gate complete may the human run `scripts/canary-arm`.

### Genuine Canary dry run completed — 2026-10-02

Candidate 3112 arrived after the active dry-run cutoff with 36/36 active Reversal votes (100% consensus). The executor claimed it fresh, validated wallet/funding/caps/fresh Kraken FX, obtained and validated a real Jupiter entry quote, persisted a simulated position, held the original five-minute horizon, obtained a real Jupiter exit quote, and persisted the intent `closed` with `reason=simulated_exit`. `broadcast=false` throughout. The executor then fail-closed into `stopped=true, armed=false, problem=dry_run_complete`. The persisted dry-run arm gate now evaluates TRUE.

This proves the required end-to-end simulation gate. It does not itself enable live trading. The next real-money step is the explicit operator action `scripts/canary-arm`, which must re-check the dry-run gate, wallet identity, funding, fresh FX and unresolved-position state before enabling the bounded Canary.

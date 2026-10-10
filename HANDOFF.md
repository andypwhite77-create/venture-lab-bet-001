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
- Current live limits are £1 max trade, 0.003 SOL network/exit reserve, fixed Champion Canary roster, one open position maximum, no leverage/margin/borrowing. Historical sections below retain superseded consensus/floor settings for audit context.

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

## Dashboard P&L window semantics — 2026-10-03

Dashboard headline P&L now defaults to the last 24 hours and the Swarm/colony/bloodline figures use the same selected period as the chart. This prevents early experimental ledger history from being presented as current performance. The 7d/30d/90d/all-time views remain selectable and historical rows are unchanged.


## First live Canary attempt — 2026-10-02 / 2026-10-03

The operator armed the Reversal Canary after the genuine-future dry-run gate passed. Candidate 3119 qualified at 35/36 active Reversal votes (97.22%) and the executor entered the live submission path for a <=£1 SOL→token swap.

The transaction did not reach chain. Hummingbot Gateway's mandatory pre-send simulation rejected the Jupiter swap with `SLIPPAGE_EXCEEDED` (custom program error 6001 / 0x1771) because market movement pushed expected output below the quoted minimum. Independent reconciliation found the Canary SOL balance unchanged, no token account/balance for the target mint, and no new wallet transaction signature. Intent 84 was therefore reconciled from `uncertain/submission_outcome_unknown` to `rejected/gateway_slippage_exceeded`, with `broadcast=false`. The Canary remains fail-closed and stopped until an explicit operator re-arm.

`canary_executor.py` now distinguishes Gateway errors that are provably pre-broadcast (`SIMULATION_FAILED`, `SLIPPAGE_EXCEEDED`, `INSUFFICIENT_BALANCE`, `INVALID_PARAMS`, `NO_ROUTE_FOUND`) from genuinely ambiguous submission failures. Entry-side pre-broadcast rejection is safely rejected without fabricating a broadcast. Exit-side pre-broadcast rejection preserves the existing open position and stops for operator-controlled exit handling. Timeouts and landed transaction failures remain uncertain/fail-closed.

The research dashboard now reads the actual `canary_control` state instead of inferring real-money authority from historical broadcast rows. Its Authority Boundary reports ARMED / STOPPED / DISARMED plus the current problem and most recent live intent. P&L windowing remains separate: the default dashboard window is 24h, while 7d/all-time history remains selectable.

### Canary safe-reject continuity
- Live Canary still requires an explicit operator arm after a hard stop or deploy-time stop.
- Entry-side local quote-validation failures now persist a specific safe reason (for example `quote_raw_price_impact`) and reject only that opportunity; they do not disarm an already-armed Canary.
- Gateway-proven pre-broadcast entry rejection (simulation/slippage/no-route/invalid params/insufficient balance) also rejects only that opportunity and preserves arming because no transaction reached signing/send.
- Unknown exceptions, wallet/funding/FX safety failures, ambiguous submission outcomes, landed failures, and any exit-side execution problem remain fail-closed and disarm/stop the Canary.
- Regression coverage verifies the entry/exit distinction; suite is 96/96 passing at commit `8f46cd7`.

### Canary reality-test trigger (2026-10-03)
- Live Reversal trigger now mirrors the paper path: one active Reversal ant is sufficient to create an eligible intent; the former 80% consensus gate is removed.
- £1 remains the hard per-trade cap and only one live position may exist at a time.
- The former £4 wallet floor is removed for this deliberately expendable tiny bankroll; 0.003 SOL remains untouchable as the network/exit reserve.
- Quote validation, wallet identity, fresh Kraken FX, no leverage, ambiguous-submission fail-closed behavior, and exit-side hard stops remain unchanged.
- Existing pre-change rejected intents remain historical evidence and are not replayed; arming sets a fresh eligibility timestamp.

## Forward development tracks — 2026-10-03

The agreed forward roadmap is now captured in `docs/DEVELOPMENT_ROADMAP.md`. Priority streams are: packageable Spawn Queen / Colony Factory; bounded ant plasticity introduced only in challengers after the Elite pool reaches roughly 50; heritable plasticity envelopes with non-heritable activation state; champion/challenger promotion where new ants must outperform relevant live incumbents on fresh evidence; a stronger multi-feed Swarm Queen; blind adversarial review of Queen proposals by independent major models before operator approval; measured hosting/capacity watch; and eventual permanent live Elite status if Canary remains consistently profitable over a meaningful live sample.

Do not destabilise the current Reversal Canary while it is proving live behaviour. Develop these streams in parallel and promote only through forward evidence, Canary and explicit human approval.

## Champion League cron container fix — 2026-10-03

The recurring `venture-lab-app-run-*` containers were traced to the five-minute Champion League cron. It used `docker compose run --rm ... app`, which intentionally created a short-lived one-off app container every tick and triggered the orphan-container health warning.

The installed cron now uses `docker compose exec -T -e PYTHONPATH=/app app python scripts/champion_league_tick.py` inside the existing healthy production app container. The 14:55 UTC post-change tick completed and updated `/home/deploy/champion_league.log` without leaving any `app-run-*` container. Production app/admin/PostgreSQL/Canary remained healthy. Preserve this `exec` form when recreating the cron; do not restore the former `compose run` form.

## Bounded live inventory recovery — 2026-10-03

The first genuine live Canary round trips exposed an exit-state bug: a live entry could land, then a later local exit quote validation failure (`quote_price_impact`) incorrectly marked the intent rejected. Two real token positions (intents 102 and 107) remained in the wallet while the executor believed they were rejected. Both entry signatures were independently verified finalized and the exact token balances were verified on-chain.

Commit `29117b6` adds an explicit Recovery state and exit-only recovery mode. At the original strategy horizon the ant's result is frozen separately. A losing or unsafe exit transfers inventory to Recovery; Recovery may only sell, never add/average down, re-quotes every 15 seconds for up to 15 minutes, exits immediately at break-even-or-better, and at the deadline accepts the first otherwise-safe quote. If no safe route exists at the deadline it fail-closes and retains the token for operator review. New entries are impossible in `recovery_only` mode.

Commit `6e17050` separates strategy/recovery basis from treasury plumbing cost. Recovery compares the exit to the actual swap input (`entry_trade_sol` / entry quote amount), not the full wallet SOL delta that may include one-time token-account rent and transaction plumbing. Full wallet-delta treasury P&L and trade P&L are recorded separately on close. Regression suite: 103/103 passing.

The two historical bug exposures were migrated to `status=recovery` only after proving their successful on-chain entries and current token balances. Recovery-only execution was explicitly enabled; normal Canary remained unarmed. Operator stop still means no transactions. `scripts/canary-recover` explicitly enables exits-only recovery and starts the executor.

## Canary rent reclamation — 2026-10-04
- Seven empty speculative Token-2022 accounts currently hold 0.01059688 SOL of reclaimable rent; USDC is deliberately excluded.
- Gateway now has a narrowly scoped close-token-account route: destination is always the same Canary wallet, token owner/mint/program/zero balance are revalidated on-chain, and the wallet key remains inside Gateway.
- `./scripts/canary-rent-reclaim simulate` discovers eligible closed-live Canary mints and simulates closures; all seven current accounts pass.
- `./scripts/canary-rent-reclaim execute-one` is intentionally limited to exactly one live account and never retries an ambiguous submission.
- The first generic sender implementation produced failed compute-budget transactions; all seven accounts remained open. It cost about 0.00002065 SOL total. The route was changed to the signed raw-transaction pattern used by Gateway's existing Solana unwrap path.
- Automatic rent reclamation is NOT enabled yet. Require one successful live close and on-chain/wallet reconciliation before scheduling it.
- Git implementation commit: 70ba2ef.

## Swarm strategic-review reliability — 2026-10-04
- Recurrent 45s ReadTimeout after campaigns 39 and 40 traced to a hard strategic-review HTTP timeout, not host contention.
- Strategic review is now queued by Breeding Queen and processed asynchronously by Swarm Queen; campaign/cooldown progression never waits for advisory model latency.
- Strategic-review timeout raised from 45s to 120s only; normal Swarm loop remains unchanged and research-safe.
- Stale `running` strategic requests older than 10 minutes are recovered to pending after daemon interruption.
- Validation: an older pending review completed successfully in 66.17s, which would have failed under the old 45s limit. Campaigns 39 and 40 were selectively requeued from saved evidence and both completed successfully without rerunning either campaign.
- Restart testing exposed a separate cadence bug: restarting `queen-survival` bypassed the 24h campaign cooldown and launched campaign 41 early. Campaign 41 completed and is retained as real history; no records were falsified or deleted.
- Breeding cooldown is now restart-safe using the persisted `queen_survival_state.json` completion timestamp. Verified live after restart with `breeding_cooldown_resumed` and ~86,259s remaining.
- Full colony suite passed: 105 tests.
- Commits: `739c0c6` (non-blocking strategic reviews), `e0f02df` (restart-safe Queen cooldown).

## Shadow Swarm Recovery Assessment — 2026-10-04
- Added `colony/recovery_assessment.py`: auditable Swarm Queen classifier for `NORMAL_FLUCTUATION`, `GENUINE_SLIDE`, or `UNCERTAIN`.
- Classifier is advisory-only: no Gateway execution, wallet signing, Canary control mutation, risk-limit changes, or trade authority.
- Full evidence is persisted; model receives a compact bounded snapshot. Malformed/time-out output fails to `UNCERTAIN`.
- Historical replay is strictly cut off at each Recovery deadline. An initial replay that admitted later same-token observations was marked `superseded_lookahead`; it is retained for audit and must not be treated as valid evidence.
- Corrected shadow checks: intent 117 (deadline loser) -> `GENUINE_SLIDE`; intents 114/118/119/120 -> `NORMAL_FLUCTUATION`. The latter had already reached break-even/better within Recovery, so they are sanity checks, not independent predictive proof.
- Intent 130 deadline snapshot: strategy horizon -14.34%; last executable-min Recovery estimate -6.62%; Queen classified `NORMAL_FLUCTUATION` (0.85 confidence).
- Later read-only live quote for intent 130 deteriorated to roughly -30% to -33% vs trade basis; current reassessment flipped to `GENUINE_SLIDE` (0.95 confidence). No sell was submitted.
- Qwen3 4B was tested but is too slow for the current host/deadline path (one 60s timeout; one ~49s answer). Fast primary remains qwen3:1.7b; prose is non-authoritative.
- Swarm daemon processes Recovery assessments in its own async task, separate from normal five-minute Swarm and strategic-review work.
- Regression suite: 110/110 passing. Git commit `c2a89f5`.
- Canary executor was not rebuilt or modified by this deployment. Intent 130 remains `recovery`, no exit signature, Canary remains stopped pending explicit next-step decision.

## Queen-guided live Recovery — 2026-10-04
- Canary Recovery now consumes bounded Swarm Queen assessments after the original 15-minute recovery window; Queen remains advisory and has no wallet/signing authority.
- Recovery target is +0.50% on the safe executable minimum versus trade basis, providing a small buffer over recent ~0.32% round-trip chain fees.
- At/after deadline: NORMAL_FLUCTUATION >=0.70 confidence keeps holding for the small-profit target and triggers reassessment every 60s; GENUINE_SLIDE >=0.70 becomes sticky `exit_first_safe`; UNCERTAIN/low confidence/malformed/90s timeout also becomes `exit_first_safe`.
- `exit_first_safe` never relaxes quote/slippage/price-impact validation; if a quote is unsafe or Gateway rejects pre-broadcast, Recovery keeps inventory and retries rather than disarming Canary.
- Routine recovery deadline/quote events no longer call `halt()`. One-position discipline still prevents fresh entries while a recovery row is active.
- Existing safety halts remain for genuinely ambiguous/failed transaction states and unexpected executor faults.
- Validation: 113/113 tests pass; deployed executor reports target_bps=50, recheck=60s, wait=90s, min_confidence=0.70, and no deadline halt path.
- Pre-arm verification: Canary remains stopped/disarmed; intent 130 remains recovery with no exit signature; no operational (`shadow=false`) Recovery assessment has fired.
- Commit: `ca88b6d`.

## Queen recovery cleanup and accounting v2 — 2026-10-04
- Fixed recovery-assessment audit mode: operational requests now emit `shadow=false` and `mode=operational`; shadow replays emit `mode=shadow`.
- Superseded look-ahead/parser-development assessment rows remain preserved but are terminal audit records, not unfinished work.
- #130 closed successfully after Queen classified `GENUINE_SLIDE` at 0.95 confidence; `exit_first_safe` remained sticky through pre-broadcast slippage rejects until a safe exit landed.
- Canary remained armed throughout the recovery/exit sequence.
- Canary close accounting now separates trade basis, wallet deltas, network fees, non-trade entry overhead, gross exit, market P&L, market P&L after network fees, and liquid-wallet delta.
- #130 is reconciled as `canary_execution_v2`: entry fee 0.000010907 SOL, exit fee 0.000009330 SOL, known recoverable rent 0.001488440 SOL, and net economic loss after known rent of about 0.001816235 SOL.
- Older eight closed live trades are explicitly tagged `legacy_v1`; they were not bulk-rewritten because the historical on-chain reconciliation batch was blocked by a platform safeguard.
- Full colony suite passed 115/115 after cleanup. Commit: f9db422.

## Champion Canary roster and Queen handoff — 2026-10-08

The Canary signal source has moved from the broad active Reversal population to a fixed Champion roster. Default roster size is five (`CHAMPION_CANARY_ROSTER_SIZE=5`). `colony/canary_controller.py` now reads current roster members from `champion_league.canary_slot` and only considers their fresh `champion_paper_entries`. It records per-intent supporting genomes, roster slots and intended holds in `canary_intent_votes`.

Automatic Canary rotation runs inside the existing five-minute Champion maintenance tick. A challenger must have >=25 genuinely fresh forward observations across >=3 days, win rate >=55%, median >=+0.25%, positive-day rate >=60%, worst forward trade >=-25%, a non-duplicate behaviour signature, and must beat the weakest Canary incumbent on forward, Arena and combined Champion score. At most one roster seat changes per tick. A seated Canary ant is protected from generic qualification expiry/duplicate culls until displaced or removed by roster resizing.

First automatic eviction: on 2026-10-08, `g_50357d0bba4d8ad9` replaced `g_bd729464d0b52699` in Canary slot 3 after reaching 25 fresh trades across three days. This did not alter signer/global arm state.

The Breeding Queen handoff is now five behaviour-distinct finalists per completed campaign instead of two. This widens prospective paper exploration only. Breeding remains 10,000 genomes per wave, two waves per campaign, 24-hour restart-safe cooldown. Spartan, Champion and Canary evidence gates are unchanged.

Intended future ladder: paper evidence -> Canary roster -> attributable per-ant Canary evidence -> live pool. A target of roughly 25 attributable Canary trades before live-pool eligibility is planned but is NOT yet an automatic rule. Human authority remains required for live enable.

Known evidence-pipeline issue: Champion paper accepts arbitrary genome hold durations, but the standard research outcome bank does not automatically request every noncanonical exact horizon. A six-minute genome can therefore accumulate Champion paper entries without corresponding six-minute scored outcomes. Do not retrospectively backfill these as prospective evidence. The correct future repair is to prospectively call `request_candidate_outcome()` when Champion records a noncanonical hold, before that horizon matures.

## Automatic rent reconciliation and 10-day trade replay — 2026-10-10

Added `colony/canary_rent_auto.py` and `scripts/canary-rent-auto` and enabled a host crontab entry at minutes 17 and 47 of each hour. Single-account finalized-zero-token reclamation only; holds shared live executor advisory lock 84619320 plus its own 84619321, validates no live claimed/open/recovery/submitting/uncertain inventory, requires historic closed mint >5m old, finalized on-chain token-account exact owner/mint/0 raw token units, Gateway simulation success, and writes the `canary_rent_reclaim_audit` record BEFORE invoking actual closure. Broadcast-unknown, reserved or submitted state blocks all further automation until reviewed. Successful close waits for account to disappear at finalized commitment. All errors fail closed, no unbounded auto-retry and no live-trading settings altered. Cron output /home/deploy/canary-rent-auto.log. First actual account returned 0.00151384 SOL, recorded confirmed; read audit table for count and signatures. Rent return does not constitute profit.

1–10 Oct audit: 32 closed live Canary positions. Eight early records missing current normalized accounting were reconstructed from finalized Solana transactions using entry trade basis, entry tx fee and exit wallet delta; total market P&L after network fees -0.00656298853091 SOL = about -£0.5442 at 82.92 GBP/SOL. Total recorded measured network fees 0.001044711 SOL (~£0.0866). A hypothetical fivefold stake on identical 32 trades at exactly matching percentage market outcomes, fixed historical network fees, no price impact deterioration and sufficient capital gives -0.02863609865455 SOL = about -£2.3745. It is an optimistic linear sensitivity rather than a historical executable quote simulation; actual £5 fills may be poorer, rejected or impossible. Trading P&L excludes locked token-account rent, changing exchange rates and outside deposits.

## Reversal parent downgrade and bounded recovery — 2026-10-09

The reported fall from two proven Reversal parents to zero occurred on 2026-10-09 between 11:46 and 11:51 Europe/London time. No births, culls or deactivations occurred at the transition. Both selected parents remained alive but switched to relative_tail_repair because fresh paper evidence crossed unchanged reliable-parent quality gates. g_103fe8a53ab91b13: n23, win 52.17%, median +0.229%; g_d20b45ea6d9be79a: n50, win 52.0%, median +0.962%. Both retain positive mean and sub-25% worst observed trade. The shared 5-minute outcome at candidate 5144 was about -7.12% and preceded the downgrade.

To prevent full-population breeding stagnation without weakening evidence qualification, the research-only Reversal turnover rule now allows early replacement at n>=20 only for an ant with BOTH win rate <40% and negative median. The normal n>=25 mature-underperformer turnover and 20-nonbaseline-survivor floor remain. Current Champion elites and Canary-seat holders are protected from this turnover; protection does not confer reliable-parent status or live authority. First deployment confirmed retirement of g_1be9a305f61020fb (n21, wins ~38%, median negative) and birth of g_1eda475127648857, preserving population 36. Parent identity, class, gate-failure reasons, population room and breeding wait reason are now logged each tick.

The Spartan alumni evolution summary now includes two separately genome-labelled objects, most_observations and highest_average, alongside legacy scalar fields. The high-observation ant g_621ca8d3ebe1ed8a had n60 but average ~-0.95%; the +11.67% average belongs to g_2298a9dcd705daec with only n12. These must never be merged into one fictitious ant. The sealed Spartan exam remains unchanged.

## Admin trading desk — 2026-10-09

The private admin console now has a read-only trading desk powered by `colony/admin_analytics.py` and `GET /admin/api/analytics?window=...`. Supported windows are 24h, 7d, 30d, 90d and all-time.

Server-side analytics are the accounting authority for the UI. They calculate realised live Canary P&L after network fees, economic-equity curve, per-trade P&L, cumulative P&L, cumulative fees, running win rate, profit factor, max drawdown, current wallet cash, spendable cash above the 0.003 SOL reserve, open/recovery/uncertain positions, rejection reasons, roster state, challenger promotion progress and equal-share voter attribution. The browser only renders these values.

The admin UI provides adjustable chart metric/window selectors plus tables for positions, real Canary fills, execution quality, Canary seats, promotion race and ant contribution. It intentionally has no manual order-entry ticket and grants no new execution authority.

The stale £4 admin wallet/component floor has been migrated to £0 to match current Canary execution configuration. The real reserve remains 0.003 SOL and the real max trade remains £1. Deployment restarted only the admin service; Canary controller/executor were not rebuilt or restarted.

## Economic survival objective and market snapshots — 2026-10-10
Both Swarm and Breeding Queen now explicitly describe survival as repeatable positive net economic surplus after fees and losses, with bounded left-tail risk. These are instructions/telemetry objectives; they do NOT rewrite fitness formulas, override sealed Spartan gates, grant any trading authority, or prove profitability. `research._record` now archives the market payload before duplicate-candidate cooldown, so suppressed candidates no longer silently suppress their market snapshot. This improves one previously uncovered data path, but does NOT constitute universal raw-provider capture. Existing `market_snapshots`, `research_candidates`, and `research_price_path` remain research-history stores; Spartan holdout and prospective evaluation must remain isolated from training. Future work: build independent append-only provider-ingress event log with fetch metadata/errors, lineage and retention monitoring, then gate model evaluation by economic expectancy and worst-case downside.

## Colony organism objective — 2026-10-10
User's north star is an aggressive, expansion-minded *research persona*: the Swarm Queen scouts markets and proposes networked specialist colonies; Breeding Queen evolves competing strategy lineages. Both share the `ORGANISM_DRIVE` in `colony/queen_roles.py`, with net risk-adjusted surplus and tail control as the economic survival constraint. This is a personality/mission directive, NOT agent autonomy to trade, provision infrastructure, self-replicate, use sealed Spartan answers, or enlarge financial risk. All existing authority boundaries remain intact. Expansion to ETH, new venues and meshed colonies remains a research proposal until separately approved and tested.

## Approved research and colony mesh foundations — 2026-10-10
Added append-only non-authoritative `colony_market_ingress` observations with timestamp, venue/provider, original provider response, failures, token, size and research colony source. Captured through `colony.provider_hub.market_snapshot` and every GeckoTerminal trending item before candidate filters in `research.run_research_cycle`; duplicate-cooldown market snapshots are retained independently. Not every external provider endpoint is yet instrumented. Errors warn and do not modify wallet controls. Registry `colony_mesh_registry` contains solana_research/paper_research, ethereum_scout/research_proposed, cross_venue_scout/research_proposed with allocation_authorized=false enforced by DB checks; it represents a research topology, not launched trading colonies.

Added `capital_preservation_shadow_v1` to evaluate immutable pre-entry market-feature filters against matured paper outcomes and persist `capital_preservation_shadow_runs`. It has no execution hook. Initial retrospective sample of 203 five-minute outcomes: 77 pass, mean +0.616%, and 126 veto, mean -3.258%; severely confounded by selection/missing data/fee assumptions and not a causal or live execution result. No trade authority or sizing changes. Champion forward paper entries now prospectively request their exact hold-minute outcome when registered, avoiding missing noncanonical horizons without historical lookahead. Existing Queen selection fitness already gates both train/validation profitability and penalizes negative tails, low liquidity and outlier concentration; no arbitrary fitness rewrite is warranted before a comparative test.

## Human sovereign proposal gate — 2026-10-10
Introduced `colony.queen_opportunity_queue` with evidence-backed research proposals, explicit risk/failure modes and requested resources, immutable-ish status transitions from proposed to research_approved or rejected, and an authenticated /admin/api/queen-proposals read/create/review API. Mutations require existing admin session + CSRF and write audit events. Research approval does NOT authorize spending, trading, new credentials, leverage, access to other systems, or market interference. No automated executor consumes approvals. Broad lawful short/dislocation/cross-venue theses are eligible for investigation; market manipulation is not. Further iteration: make Swarm automatically originate *supported* proposals through this queue and render the morning decision dashboard.

## Adversarial Queen morning opportunity scout — 2026-10-10
Added `colony/queen_proposal_scout.py`: deterministic read-only assessment of Canary route rejections and market-feed blind spots, with evidence-backed human-review research proposals only. It cannot place trades or provision compute. One scan per Europe/London calendar day persisted in `queen_proposal_scout_runs`; duplicate proposal themes limited to seven days. Host cron runs 07:07 Europe/London server local time only if the host timezone is set appropriately (verify timer TZ), logs `/home/deploy/queen_proposal_scout.log`. First run created two proposals: execution-route reconnaissance and degraded feed resilience, against 37 blocked signals and 23 feed unavailable records. User requested a companion Google Doc "Venture Lab — Swarm Applications Log" with one short non-trading application note at every future update. Document ID: 1KY4zc8EtC0RcWom5euUB2SyYOOOR-Zxvdbe1NIJU-P0; append to it with connected Google Drive tools as part of future updates. Human-authorized research does not grant execution.

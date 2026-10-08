# Live Promotion and Treasury Control

## Promotion states

Ants are tagged by strategy family and lineage. `live_candidate` is a discovery/deployment tag only; it grants no execution authority.

The intended promotion path is:

`reference-testing -> canary-ready -> canary-running -> live-ready -> live`

A genuine Spartan pass moves an ant to `canary-ready`. A canary pass may move it to `live-ready` only when the Spartan pass is already recorded. `live-ready` still has no trading authority. A separate authenticated human action is required to set `live_authorized=true` and enter `live`. The global live-stop overrides all per-ant authority.

The five Eve v2 reference ants are registered as `reference-testing` across reversal, momentum, order-flow, pullback and liquidity families. The naive control is intentionally excluded.

The five frozen Eve v3 Beast Cohort ants are also registered as `reference-testing` across pullback, accumulation, compression, exhaustion and drawdown-reversal families. They begin forward paper evidence only after the v3 freeze and do not inherit v2 paper history.

## Canary profiles

The existing Reversal canary remains unchanged and consensus-based. Individual Spartan graduates and Eve reference ants use the registry profile `individual-ant-v1`; this is a routing contract for the future individual-ant canary runner and does not reuse the Reversal consensus exam.

## Treasury policy

Treasury policy is disabled by default. Configuration includes:

- personal-wallet public address selected from the admin wallet registry
- realized-profit withdraw percentage and reinvest percentage; they must total 100%
- cash-out threshold and reinvest/stake-step threshold
- minimum operating bankroll
- maximum family exposure percentage
- maximum per-ant stake
- independent auto-withdraw enable switch

Profit allocation uses a portfolio high-watermark. Losses must be recovered before further profit is allocated. This prevents withdrawals from consuming principal after a run of wins followed by losses.

Reinvested profit belongs to a colony-level growth bucket rather than automatically compounding the winning ant. Future stake allocation must obey both the per-ant ceiling and family-exposure cap.

## Execution boundary

The registry and treasury module do not hold signing keys and cannot transfer funds. Wallet signing remains isolated. Auto-withdraw configuration is policy state only until a dedicated, fail-closed settlement worker is connected to the signer and explicitly armed.

## Eve reference forward paper trading

The five frozen Eve v2 reference ants continuously evaluate new research candidates in `eve_reference_paper_entries`. They have no signer or live authority and cannot mutate in the paper runner. An ant cannot open overlapping positions in the same mint; its hold horizon is the minimum re-entry interval.

Closed forward outcomes are included in Queen prospective experience. Their mints are immediately quarantined from Queen validation and sealed holdout. A reference ant must accumulate at least five unique forward mints before it can influence descendants, and it must still satisfy the normal positive-career quality rules before its frozen genome is offered as a gene-seed template. Spartan answers are never fed into this path.

## Champion / Challenger League (2026-10-02)

The research promotion model now uses five incumbent **Elite** behaviours rather than treating Spartan as a binary executioner. The founding Elite are the five best distinct full-period Reversal behaviours from the forward tournament; duplicate entry signatures are collapsed so clones cannot manufacture consensus.

All other existing candidates enter **Qualification**. The latest two Queen finalists from each observed Queen run are admitted to Qualification; the rest remain research history rather than bloating the active challenger pool. Qualification is continuously ranked in a public **Spartan Arena** over the broad historical dataset, while each challenger also accumulates prospective paper evidence from its enrollment cutoff.

A challenger may replace the weakest Elite only when it is behaviourally distinct, has at least 25 forward observations across at least three days, and beats the incumbent on both conservative historical Arena score and conservative forward score. Arena results are intentionally not a sealed exam and may be used as ranking evidence. The existing sealed Spartan exam remains separate and is not fed back into breeding.

`colony/champion_league.py` owns the research league. `scripts/champion_league_tick.py` performs a signer-free maintenance tick: seed/retain incumbents, admit the latest Queen top five behaviour-distinct finalists, capture new forward-paper opportunities, refresh Arena ranking, and apply research-pool promotions. A five-minute cron runs this research-only tick under `flock`; it has no wallet, signer, or broadcast authority.

Real-money Canary execution remains a separate human-controlled layer and is not automatically armed by Elite status or league promotion.

## Cumulative Qualification Corpus and Elite control

`qualification_corpus` is the permanent append-only benchmark for Champion League replay. Every completed `research_candidates` / `research_outcomes` horizon is copied once with the market/features observed at decision time. Existing corpus rows are never updated. Dynamic model-vote features are deliberately excluded from replay so later models cannot rewrite old benchmark inputs.

New challengers can therefore be fast-tracked through the full accumulated corpus immediately. Chronological and forward evidence remain distinct: Arena replay can establish competitiveness quickly, but promotion still requires at least 25 genuinely post-enrollment forward observations across at least three days and must beat the weakest Elite on both Arena and forward scores.

The admin control plane exposes the five Elite incumbents, the top Qualification leaderboard and corpus coverage. It also stores an operator-requested Elite capital mode (`off`, `canary`, `live`). This state is intentionally separate from execution authority: league promotion never grants money access, global live-stop forces the requested mode back to `off`, and `live` remains blocked unless a separate execution bridge is explicitly connected.


## Reversal Canary hardening — 2 October 2026

The Reversal Canary is an isolated, human-gated execution path with £1 maximum trade size, £4 wallet floor, >=80% active-Reversal consensus, one-position maximum, fresh Kraken SOL/GBP validation, Jupiter quote validation and fail-closed crash reconciliation. The controller creates intents but owns no broadcast capability; the executor/signer path remains disarmed until the dry-run gate is satisfied and the operator explicitly arms it.

Two late hardening fixes are safety-relevant. First, the controller now excludes already-seen candidate IDs before applying its 50-row query limit; previously it could repeatedly read an old first page and silently miss newer signals. Second, execution sizing is recalculated at fresh SOL/GBP at execution time and may only shrink from the stored intent amount, so FX appreciation cannot turn an originally <=£1 intent into either an accidental oversize or a spurious rejection.

A qualifying dry run must use a genuine future Reversal signal, claim it within the freshness window, validate all limits, acquire and validate a real Jupiter entry quote, persist a simulated open position for the strategy's original hold time, obtain the corresponding exit quote and persist the position closed. Historical/stale ready intents cannot satisfy the arm gate.

### First qualifying end-to-end dry run

On 2 October 2026, candidate 3112 satisfied the live dry-run requirement with 36/36 active Reversal votes. The executor completed the genuine future path using real Jupiter entry/exit quotes and the original five-minute hold, persisted the intent closed, and never broadcast a transaction. After the simulated exit the control latched `problem=dry_run_complete`, `stopped=true`, `armed=false`; the arm-gate query evaluates true. Live trading still requires the operator to run `scripts/canary-arm` explicitly.


## First live-attempt reconciliation

The first armed Reversal Canary opportunity (candidate 3119, 35/36 consensus) reached Hummingbot Gateway but failed its mandatory pre-send simulation because Jupiter slippage tolerance was exceeded. No transaction landed: SOL balance remained unchanged, no target-token account appeared, and no new wallet signature existed. The attempt is recorded as `gateway_slippage_exceeded`, not as a live fill.

Executor handling now separates definitive pre-broadcast Gateway rejections from ambiguous submission outcomes. A pre-broadcast entry rejection never becomes a fill; an exit rejection preserves the already-open live position. Network/confirmation ambiguity still stops the Canary and requires reconciliation. This keeps the system conservative without treating known simulation failures as unknowable broadcasts.

### Canary safe-reject continuity
- Live Canary still requires an explicit operator arm after a hard stop or deploy-time stop.
- Entry-side local quote-validation failures now persist a specific safe reason (for example `quote_raw_price_impact`) and reject only that opportunity; they do not disarm an already-armed Canary.
- Gateway-proven pre-broadcast entry rejection (simulation/slippage/no-route/invalid params/insufficient balance) also rejects only that opportunity and preserves arming because no transaction reached signing/send.
- Unknown exceptions, wallet/funding/FX safety failures, ambiguous submission outcomes, landed failures, and any exit-side execution problem remain fail-closed and disarm/stop the Canary.
- Regression coverage verifies the entry/exit distinction; suite is 96/96 passing at commit `8f46cd7`.

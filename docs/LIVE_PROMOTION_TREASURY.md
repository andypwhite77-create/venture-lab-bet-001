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

`colony/champion_league.py` owns the research league. `scripts/champion_league_tick.py` performs a signer-free maintenance tick: seed/retain incumbents, admit the latest Queen top two, capture new forward-paper opportunities, refresh Arena ranking, and apply research-pool promotions. A five-minute cron runs this research-only tick under `flock`; it has no wallet, signer, or broadcast authority.

Real-money Canary execution remains a separate human-controlled layer and is not automatically armed by Elite status or league promotion.

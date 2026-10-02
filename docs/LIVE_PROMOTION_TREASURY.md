# Live Promotion and Treasury Control

## Promotion states

Ants are tagged by strategy family and lineage. `live_candidate` is a discovery/deployment tag only; it grants no execution authority.

The intended promotion path is:

`reference-testing -> canary-ready -> canary-running -> live-ready -> live`

A genuine Spartan pass moves an ant to `canary-ready`. A canary pass may move it to `live-ready` only when the Spartan pass is already recorded. `live-ready` still has no trading authority. A separate authenticated human action is required to set `live_authorized=true` and enter `live`. The global live-stop overrides all per-ant authority.

The five Eve v2 reference ants are registered as `reference-testing` across reversal, momentum, order-flow, pullback and liquidity families. The naive control is intentionally excluded.

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

# Eve reference ant benchmarks

## v2 — active baseline

`eve_reference_ants_v2.json` is the current frozen benchmark. It was designed after the missing-data correction, using only missingness-safe historical inputs and three chronological walk-forward folds. Five strategy ants are positive in every fold; the sixth ant is a naive control that fails the newest fold.

The v2 freeze is **not** a Spartan pass. Its independent proof set begins at the recorded `prospective_after` timestamp. Only assets first observed after that timestamp may count as prospective evidence. Run `scripts/eve_reference_prospective_audit.py` to inspect that evidence.

Swarm Queen may use v2's pre-proof strategy/sensor coverage as research landmarks. Spartan and future prospective outcomes are deliberately excluded from Swarm breeding inputs.

## v1 — diagnostic only

`eve_reference_ants_v1.json` is retained as design-time forensic evidence. Raw v1 Spartan output is intentionally kept outside the repository and runtime build context so future design work cannot accidentally learn exam answers. The v1 exercise exposed a representation bug: GeckoTerminal token-level fallback data encoded unavailable pool metrics (5m/1h price change, volume and transactions) as literal zero. That made distinct genomes collapse onto the same apparent Spartan behaviour.

No v1 result is valid evidence for or against a strategy. Pre-v10 Spartan exams have been marked inconclusive and excluded from Queen drought pressure.

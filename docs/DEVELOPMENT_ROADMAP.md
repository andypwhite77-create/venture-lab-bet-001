# Venture Lab Development Roadmap — 2026-10-03

## Guiding rule
Do not destabilise the live Reversal Canary while it is proving itself. New intelligence and experimentation should be developed in parallel, promoted only through forward evidence, Canary and explicit human approval.

## 1. Packageable Spawn Queen / Colony Factory
Turn the current Spawn/Breeding Queen stack into a portable deployment package for new markets. A new colony should be created primarily by configuration: market/coin, venue, data feeds, execution connector, allowed strategy families, capital/risk envelope, evidence gates, resource caps, dashboards and recovery documentation.

Target architecture: Swarm Queen -> Colony Blueprint -> deterministic deployer -> new market colony. A spawned Queen begins with research authority only; live execution remains disconnected until evidence and human approval.

## 2. Bounded plasticity for ants
After the Elite population reaches roughly 50, introduce bounded plasticity first in testing/challenger ants. Core genome identity remains fixed. Each ant may make small temporary adaptations inside an inherited envelope: threshold offsets, hold-time bias, cooldown, confidence and later stake preference.

Adaptations must be reversible, evidence-driven, decay toward baseline unless reinforced, and fully logged. Plasticity never permits arbitrary self-rewriting or bypass of Queen/evidence/live-risk gates.

## 3. Heritable plasticity
Separate three layers: genome, plasticity envelope and activation state. Genome and plasticity envelope may be inherited; activation state does not carry over automatically. Descendants inherit the capacity to learn, not the learned response itself.

The Queen may decide whether plasticity is activated during testing. Successful envelope width, adaptation speed, decay rate and evidence requirements can themselves become evolvable/heritable traits.

## 4. Champion/challenger promotion
Once the Elite pool is near 50, growth stops being the default. New ants must outperform the relevant current live traders on fresh forward evidence before promotion. Compare net expectancy, drawdown, consistency, tail behaviour, sample size and ideally matched opportunities. Promotions replace or demote weaker incumbents rather than endlessly expanding the live pool.

## 5. Swarm Queen market-intelligence upgrade
As breeding demand falls, redirect compute to a stronger Swarm Queen. Connect multiple major independent API feeds covering exchange/DEX data, wallet/on-chain flows, liquidity, volatility, derivatives and other evidence that proves useful. The objective is a continuously updated crypto world model, not merely more raw data.

The Swarm Queen may research, hypothesise, request experiments and propose new species/markets, but does not gain unilateral authority to move money or weaken live safety gates.

## 6. Adversarial AI research council
Before a Swarm Queen proposal reaches the operator, submit the same evidence pack independently to two major external models (initial candidates: OpenAI and Gemini). One critique should focus on quantitative/statistical failure modes; the other on market/system/causal failure modes. Initial reviews should be blind to each other.

The Queen receives both critiques and must rebut, narrow or withdraw the proposal. Preserve the full proposal/critique/rebuttal/evidence trail. Over time score critics by which objections later proved valid, allowing the review board itself to become evidence-weighted.

## 7. Hosting/capacity watch
Do not upgrade hosting by intuition. Track CPU saturation, RAM pressure, PostgreSQL latency, candidate-processing lag, Queen iteration time, Gateway/Jupiter latency, disk I/O and event-loop delays. Upgrade or split infrastructure only when measured bottlenecks show a tangible benefit.

Likely long-term shape: lightweight, boring live-trading node separated from a heavier research/breeding/Swarm-Queen node. A research experiment must never be able to starve or destabilise live execution.

## 8. Live progression
Let the current Canary compound its tiny bankroll under the ants' existing trading rules. If it remains consistently positive over several weeks and a meaningful number of genuine round trips, graduate the proven Elite pool to permanent live status. Canary then remains the proving ground for new ants, plasticity, strategy changes and new coins.

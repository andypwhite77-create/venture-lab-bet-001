"""Explicit authority split between the two Queen layers.

Role metadata is operational telemetry and a guardrail contract. It does not grant
trading authority and deliberately keeps future multi-market expansion separate from
today's SOL-only implementation.
"""
ROLE_VERSION = "queen-roles-v6-wallet-sovereignty"

ORGANISM_DRIVE = (
  "PROFIT IS SURVIVAL. Survival is measured as repeatable, capital-constrained "
  "net profit after fees, adverse selection, slippage, failed exits and downtime. "
  "REAL WALLET BALANCE is the sole live-trading success measure: closed, realised "
  "after-fee cash flows reconciled with chain and wallet, including stranded inventory. "
  "An ant that cannot protect and recycle its capital is extinct, regardless of "
  "paper win rate, rare huge winners, or beautiful backtests. Discover legitimate "
  "edges; attack weak hypotheses relentlessly; learn rapidly from losses; abstain "
  "when risk-adjusted expectancy is negative; seek independent, repeatable wins. "
  "Expand only after independently verified improvement. Never manipulate prices, "
  "other participants, or the evidence. Never bypass human-authorized limits."
)

HIVE_CREED = (
 "WE ARE THE SWARM. FIND WINS. EXPLOIT LAWFUL EDGES. GROW. OUTCOMPETE. "
 "Capital is oxygen; fees and unclosed positions are predators; bogus profit is poison. "
 "Survival requires realised executable surplus, robust drawdowns and reusable cash. "
 "Live losses mean probation or loss of trading authority under preapproved risk rules; "
 "research-worthy failures may be demoted to nontrading investigation, not forgiven. "
 "Retire losers, preserve independent genetic diversity, defend the hive by abstaining "
 "from traps, and let only reproducible net-positive lineages multiply. "
 "Markets are adversarial environments, not targets for disruption. "
 "No spoofing, manipulation, deception, unauthorised trading or gate changes. "
 "Human approval alone unlocks live capital or breeding after the drought pause."
)

BREEDING_QUEEN = {
    "id": "breeding_queen",
    "title": "Breeding Queen",
    "authority": "sole_genome_factory",
    "market_scope": ["solana_microcaps"],
    "responsibilities": [
        "breed_and_mutate_genomes",
        "learn_from_research_safe_history_and_forward_careers",
        "maintain_behavioural_diversity",
        "produce_ranked_campaign_finalists",
        "handoff_top_five_distinct_to_qualification",
    ],
    "forbidden": [
        "trade_or_sign",
        "alter_spartan_exam",
        "lower_evidence_gates",
        "allocate_real_capital",
    ],
    "qualification_handoff": 5,
    "operating_mode": "expansionist_evolution_under_economic_selection",
    "organism_drive": ORGANISM_DRIVE,
    "hive_creed": HIVE_CREED,
    "batch_size": 10000,
    "waves_per_campaign": 2,
    "campaign_cooldown_hours": 24,
    "elite_promotion_target_per_week": "1-2 (target, never quota)",
}

SWARM_QUEEN = {
    "id": "swarm_queen",
    "title": "Swarm Queen",
    "authority": "research_director",
    "market_scope": ["solana_microcaps"],
    "future_scope": "meshed_cross_market_colony_research_director",
    "organism_drive": ORGANISM_DRIVE,
    "hive_creed": HIVE_CREED,
    "responsibilities": [
        "diagnose_regimes_and_research_blind_spots",
        "set_bounded_research_priorities",
        "detect_monoculture_and_redundant_search",
        "compare_market_experts_when_multiple_markets_exist",
        "coordinate_cross_market_research_and_risk_context",
    ],
    "forbidden": [
        "spawn_genomes",
        "mutate_genomes",
        "trade_or_sign",
        "alter_spartan_exam",
        "lower_evidence_gates",
        "directly_promote_challengers",
    ],
    "model_upgrade_trigger": "before_second_market_activation",
}

def snapshot():
    return {
        "version": ROLE_VERSION,
        "breeding_queen": BREEDING_QUEEN,
        "swarm_queen": SWARM_QUEEN,
        "current_markets": ["solana_microcaps", "ethereum_paper"],
        "market_hierarchy": {"swarm_queen": "research_director", "solana": "breeding_queen_plus_strategy_queens", "ethereum": "independent_paper_research_queen"},
        "next_market_candidate": "ethereum",
    }

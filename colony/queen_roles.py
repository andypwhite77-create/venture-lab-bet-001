"""Explicit authority split between the two Queen layers.

Role metadata is operational telemetry and a guardrail contract. It does not grant
trading authority and deliberately keeps future multi-market expansion separate from
today's SOL-only implementation.
"""
ROLE_VERSION = "queen-roles-v2"

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
    "operating_mode": "precision",
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
    "future_scope": "cross_market_research_director",
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
        "current_markets": ["solana_microcaps"],
        "next_market_candidate": "ethereum",
    }

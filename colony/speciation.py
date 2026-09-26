"""Evidence-gated speciation for Colony V2.
Core may propose novelty; deterministic gates decide whether it gets ants.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from colony.genome import canonical

@dataclass(frozen=True)
class SpeciationPolicy:
    min_independent_entities: int = 8
    min_observations: int = 20
    min_novel_features: int = 1
    initial_scouts: int = 12
    max_experimental_families: int = 8
    require_forward_test: bool = True

def feature_set(genome: dict[str, Any]) -> set[str]:
    return set(genome.get("parameters", {}))

def novelty(candidate: dict, existing: list[dict]) -> dict:
    cf = feature_set(candidate)
    best_overlap, nearest = 0.0, None
    for g in existing:
        gf = feature_set(g)
        union = cf | gf
        overlap = len(cf & gf) / len(union) if union else 1.0
        if overlap > best_overlap:
            best_overlap, nearest = overlap, g.get("family")
    return {"nearest_family": nearest, "feature_overlap": round(best_overlap, 4),
            "novel_features": sorted(cf - set().union(*(feature_set(g) for g in existing)))}

def evaluate_proposal(proposal: dict, existing: list[dict], policy: SpeciationPolicy = SpeciationPolicy()) -> dict:
    evidence = proposal.get("evidence", {})
    nov = novelty(proposal["genome"], existing)
    reasons = []
    if int(evidence.get("independent_entities", 0)) < policy.min_independent_entities:
        reasons.append("insufficient_independent_entities")
    if int(evidence.get("observations", 0)) < policy.min_observations:
        reasons.append("insufficient_observations")
    if len(nov["novel_features"]) < policy.min_novel_features and nov["feature_overlap"] >= 0.8:
        reasons.append("not_distinct_from_existing_family")
    if not proposal.get("falsification_test"):
        reasons.append("missing_falsification_test")
    return {
        "accepted_for_scouting": not reasons,
        "reasons": reasons,
        "novelty": nov,
        "allocation": policy.initial_scouts if not reasons else 0,
        "status": "experimental" if not reasons else "rejected",
    }

def extinction_candidate(metrics: dict) -> bool:
    return bool(metrics.get("forward_complete")) and int(metrics.get("n", 0)) >= 30 and float(metrics.get("fitness", 0)) < 0

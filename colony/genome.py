"""Domain-agnostic genomes for Colony V2."""
from __future__ import annotations
import copy, hashlib, json, random
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class MutationPolicy:
    numeric_sigma: float = 0.12
    mutation_rate: float = 0.25
    min_changes: int = 1
    max_changes: int = 3

def canonical(genome: dict[str, Any]) -> str:
    return json.dumps(genome, sort_keys=True, separators=(",", ":"))

def genome_id(genome: dict[str, Any]) -> str:
    return "g_" + hashlib.sha256(canonical(genome).encode()).hexdigest()[:16]

def _mutate_number(value: float, rng: random.Random, sigma: float) -> float:
    scale = max(abs(float(value)), 1.0)
    return round(float(value) + rng.gauss(0, sigma * scale), 6)

def mutate(parent: dict[str, Any], seed: int | None = None, policy: MutationPolicy = MutationPolicy()) -> dict[str, Any]:
    rng = random.Random(seed)
    child = copy.deepcopy(parent)
    params = child.setdefault("parameters", {})
    mutable = [k for k, v in params.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not mutable:
        return child
    rng.shuffle(mutable)
    wanted = max(policy.min_changes, sum(rng.random() < policy.mutation_rate for _ in mutable))
    wanted = min(wanted, policy.max_changes, len(mutable))
    for key in mutable[:wanted]:
        old = params[key]
        new = _mutate_number(old, rng, policy.numeric_sigma)
        bounds = child.get("bounds", {}).get(key)
        if bounds:
            new = max(bounds[0], min(bounds[1], new))
        candidate = int(round(new)) if isinstance(old, int) else new
        if candidate == old:
            step = 1 if isinstance(old, int) else max(abs(float(old)) * 0.01, 0.001)
            candidate = old + (step if rng.random() < 0.5 else -step)
            if bounds:
                candidate = max(bounds[0], min(bounds[1], candidate))
            if isinstance(old, int): candidate = int(round(candidate))
        params[key] = candidate
    child["mutation"] = {"parent": genome_id(parent), "seed": seed, "changed": mutable[:wanted]}
    return child

def crossover(a: dict[str, Any], b: dict[str, Any], seed: int | None = None) -> dict[str, Any]:
    rng = random.Random(seed)
    child = copy.deepcopy(a)
    bp = b.get("parameters", {})
    for key in set(child.get("parameters", {})) & set(bp):
        if rng.random() < 0.5:
            child["parameters"][key] = bp[key]
    child["parents"] = [genome_id(a), genome_id(b)]
    return child

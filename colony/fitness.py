"""Fitness is external to the domain and rewards robustness, not lucky P&L."""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class FitnessWeights:
    expectancy: float = 1.0
    consistency: float = 0.35
    robustness: float = 0.45
    novelty: float = 0.10
    drawdown: float = 0.80
    catastrophe: float = 1.20
    resource_cost: float = 0.10

def score(m: dict, w: FitnessWeights = FitnessWeights()) -> float:
    n = max(int(m.get("n", 0)), 0)
    confidence = min(1.0, math.sqrt(n / 30.0))
    positive = (
        w.expectancy * float(m.get("expectancy", 0)) +
        w.consistency * float(m.get("consistency", 0)) +
        w.robustness * float(m.get("robustness", 0)) +
        w.novelty * float(m.get("novelty", 0))
    )
    penalty = (
        w.drawdown * abs(float(m.get("max_drawdown", 0))) +
        w.catastrophe * float(m.get("catastrophe_rate", 0)) +
        w.resource_cost * float(m.get("resource_cost", 0))
    )
    return round(confidence * positive - penalty, 8)

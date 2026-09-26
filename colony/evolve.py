"""Deterministic evolutionary engine. LLMs propose; this layer enforces."""
from __future__ import annotations
import json, random
from pathlib import Path
from colony.genome import genome_id, mutate

ROOT = Path(__file__).resolve().parent

def load_seeds():
    return json.loads((ROOT / "seeds.json").read_text())

def make_generation(parents: list[dict], size: int = 100, seed: int = 1) -> list[dict]:
    rng = random.Random(seed)
    out, seen = [], set()
    # Preserve parents so evolution can never erase the control genotype by accident.
    for parent in parents:
        gid = genome_id(parent)
        if gid not in seen:
            out.append(parent); seen.add(gid)
    attempts = 0
    while len(out) < size and attempts < size * 50:
        attempts += 1
        parent = rng.choice(parents)
        child = mutate(parent, seed=rng.randrange(2**31))
        gid = genome_id(child)
        if gid not in seen:
            out.append(child); seen.add(gid)
    return out[:size]

def summary(population: list[dict]) -> dict:
    families = {}
    for genome in population:
        families[genome["family"]] = families.get(genome["family"], 0) + 1
    return {"population": len(population), "families": families, "unique": len({genome_id(g) for g in population})}

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--size", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--output", default=str(ROOT / "generation-1.json"))
    args = p.parse_args()
    population = make_generation(load_seeds(), args.size, args.seed)
    Path(args.output).write_text(json.dumps(population, indent=2) + "\n")
    print(json.dumps(summary(population), indent=2))

if __name__ == "__main__":
    main()

"""Bounded inheritance with protected exploration."""
import random
from colony.genome import mutate,crossover,MutationPolicy,genome_id

NORMAL=MutationPolicy(numeric_sigma=.10,mutation_rate=.25,min_changes=1,max_changes=3)
WEIRD=MutationPolicy(numeric_sigma=.35,mutation_rate=.65,min_changes=2,max_changes=5)

def offspring(parent_a,parent_b=None,seed=None,weird_rate=.05):
    rng=random.Random(seed)
    base=crossover(parent_a,parent_b,seed=rng.randrange(2**31)) if parent_b else parent_a
    weird=rng.random()<weird_rate
    child=mutate(base,seed=rng.randrange(2**31),policy=WEIRD if weird else NORMAL)
    child['inheritance']={'parents':[genome_id(parent_a)]+([genome_id(parent_b)] if parent_b else []),
                          'mode':'weird' if weird else ('crossover' if parent_b else 'mutation')}
    return child

def exploration_slots(population,share=.05):
    return max(1,round(population*share))

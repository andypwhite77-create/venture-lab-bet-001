import json
from colony.evolve import load_seeds, make_generation, summary
from colony.genome import genome_id
from colony.fitness import score

def test_generation_is_reproducible():
    a = make_generation(load_seeds(), 40, seed=42)
    b = make_generation(load_seeds(), 40, seed=42)
    assert [genome_id(x) for x in a] == [genome_id(x) for x in b]

def test_generation_is_diverse():
    p = make_generation(load_seeds(), 100, seed=7)
    s = summary(p)
    assert s["unique"] == 100
    assert len(s["families"]) == 4

def test_fitness_penalises_catastrophe():
    safe = {"n":30,"expectancy":1,"consistency":1,"robustness":1,"max_drawdown":0.1,"catastrophe_rate":0}
    dangerous = dict(safe, catastrophe_rate=0.5)
    assert score(safe) > score(dangerous)

if __name__ == "__main__":
    test_generation_is_reproducible(); test_generation_is_diverse(); test_fitness_penalises_catastrophe()
    print(json.dumps({"tests":"PASS","population":summary(make_generation(load_seeds(),100,7))}, indent=2))

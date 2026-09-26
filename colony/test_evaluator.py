from evaluator import matches
from evolve import load_seeds, make_generation
from replay import evaluate

def test_known_matches():
    seeds=load_seeds()
    assert matches(seeds[0], {"price_change_m5":-12,"dex_buy_ratio_m5":.7})
    assert not matches(seeds[0], {"price_change_m5":-3,"dex_buy_ratio_m5":.7})
    assert matches(seeds[1], {"price_change_m5":8,"volume_liquidity_m5":.2})

def test_declarative_novel_species():
    g={"family":"new_species","predicates":{"token_age_minutes":{"max":60},"transaction_acceleration":{"min":2}}}
    assert matches(g,{"token_age_minutes":20,"transaction_acceleration":3})
    assert not matches(g,{"token_age_minutes":90,"transaction_acceleration":3})

def test_shared_observation_scales_without_io():
    pop=make_generation(load_seeds(),100,seed=42)
    observations=[{"features":{},"market":{"price_change_m5":-12,"buys_m5":7,"sells_m5":3}} for _ in range(10)]
    r=evaluate(pop,observations)
    assert r["evaluations"] == 1000 and r["ants"] == 100

if __name__ == "__main__":
    test_known_matches(); test_declarative_novel_species(); test_shared_observation_scales_without_io(); print("evaluator tests: PASS")

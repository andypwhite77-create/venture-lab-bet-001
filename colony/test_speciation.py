from colony.evolve import load_seeds
from colony.speciation import evaluate_proposal

def proposal(independent=12, observations=40):
    return {
      "hypothesis":"compression followed by transaction acceleration has distinct forward behaviour",
      "genome":{"family":"volatility_breakout","parameters":{"volatility_compression_max":0.02,"transaction_acceleration_min":2.0,"hold_minutes":5}},
      "evidence":{"independent_entities":independent,"observations":observations},
      "falsification_test":"forward paper test on unseen entities",
    }

def test_good_species_gets_scouts():
    r=evaluate_proposal(proposal(), load_seeds())
    assert r["accepted_for_scouting"] and r["allocation"] > 0

def test_tiny_n_dies_at_gate():
    r=evaluate_proposal(proposal(2,4), load_seeds())
    assert not r["accepted_for_scouting"]
    assert "insufficient_independent_entities" in r["reasons"]

def test_renamed_existing_family_rejected():
    p={"hypothesis":"rename","genome":load_seeds()[0],"evidence":{"independent_entities":20,"observations":50},"falsification_test":"forward"}
    r=evaluate_proposal(p, load_seeds())
    assert not r["accepted_for_scouting"]

if __name__ == "__main__":
    test_good_species_gets_scouts(); test_tiny_n_dies_at_gate(); test_renamed_existing_family_rejected(); print("speciation tests: PASS")

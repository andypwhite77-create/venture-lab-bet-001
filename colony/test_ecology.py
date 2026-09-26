from colony.ecology import pressures

def test_evidence_gates_pressure():
    assert pressures(.1,0)["evidence_weight"] == 0
    assert pressures(.1,30)["evidence_weight"] == 1

def test_elites_gain_reproductive_access():
    assert pressures(.1,30)["reproductive_access"] > 0
    assert pressures(.5,30)["reproductive_access"] == 0

def test_tail_loss_forces_replacement_pressure():
    assert pressures(.2,30,.2)["replacement_pressure"] == 1

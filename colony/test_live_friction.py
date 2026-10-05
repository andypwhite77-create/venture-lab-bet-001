from colony.live_friction import implied_drag_bps

def test_implied_drag_matches_live_horizon_gap():
    # +2.207% paper raw versus -2.966% executable horizon ~= 517 bps drag.
    x=implied_drag_bps(2.207282524, -0.0003252407107, 0.0109649122807)
    assert 515 < x < 520

def test_live_outperformance_never_becomes_execution_subsidy():
    assert implied_drag_bps(-2.0, 0.0, 1.0) == 0.0

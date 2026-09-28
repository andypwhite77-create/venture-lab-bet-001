from colony.paper_economics import economics,adjusted_return_pct

def test_fixed_fee_creates_break_even_stake():
    e=economics(30,stake_gbp=.10,fixed_cost_gbp=1)
    assert e['net_profit_gbp'] < 0
    assert abs(e['break_even_stake_gbp']-(10/3)) < 1e-9

def test_more_stake_dilutes_fixed_cost():
    small=adjusted_return_pct(30,.10,1)
    large=adjusted_return_pct(30,25,1)
    assert large > small
    assert abs(large-26.0) < 1e-9

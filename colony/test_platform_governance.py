from colony import platform_governance as g

def test_cost_defaults_are_non_negative():
    assert g.MONTHLY_VPS_GBP >= 0
    assert g.MONTHLY_DATA_GBP >= 0
    assert g.MONTHLY_AI_GBP >= 0
    assert g.MONTHLY_OTHER_GBP >= 0

def test_live_authority_is_not_derived_in_module():
    source=open(g.__file__).read()
    assert "live_authority BOOLEAN NOT NULL DEFAULT false" in source

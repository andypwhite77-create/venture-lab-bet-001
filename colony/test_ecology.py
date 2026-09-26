from ecology import replacement_budget, should_replace, outlier_budget

def test_slow_turnover():
    assert replacement_budget(100) == 2
    assert replacement_budget(20) == 1

def test_successful_ants_are_stable():
    assert not should_replace({"state":"viable","fitness":.01},10)
    assert not should_replace({"state":"stressed","fitness":-.2},1)
    assert should_replace({"state":"stressed","fitness":-.2},4)

def test_outliers_start_tiny():
    assert outlier_budget({"independent_entities":2,"novelty":.9}) == 0
    assert outlier_budget({"independent_entities":4,"novelty":.7}) == 3

if __name__=='__main__':
    test_slow_turnover(); test_successful_ants_are_stable(); test_outliers_start_tiny(); print('ecology tests: PASS')

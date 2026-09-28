from colony.genome import genome_id
from colony.reversal_tournament import make_population,baseline_genome,score_record,catastrophic

def test_population_is_100_unique_reversal_and_baseline_preserved():
    p=make_population(100)
    assert len(p)==100 and len({genome_id(g) for g in p})==100
    assert all(g['family']=='reversal' for g in p)
    assert genome_id(p[0])==genome_id(baseline_genome())
    for g in p:
        assert -30 <= g['parameters']['price_change_m5_max'] <= -2
        assert .5 <= g['parameters']['dex_buy_ratio_m5_min'] <= .95
        assert 1 <= g['parameters']['hold_minutes'] <= 60
        assert 0 <= g['parameters']['cooldown_minutes'] <= 240

def test_lucky_moonshot_is_penalized():
    base={f'm{i}':2.0 for i in range(10)}
    steady=score_record([(f'm{i}',3.0) for i in range(10)],base)
    lucky=score_record([(f'm{i}',-2.0) for i in range(9)]+[('m9',50.0)],base)
    assert steady['tournament_score'] > lucky['tournament_score']
    assert lucky['outlier_dependence'] > .9

def test_repeated_catastrophes_hard_fail():
    rec=score_record([(f'm{i}',-30.0 if i<2 else 2.0) for i in range(10)],{})
    assert catastrophic(rec)

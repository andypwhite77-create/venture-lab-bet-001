from colony.evolution_controls import matched_random_control,epoch_fingerprint,absolute_viability

def test_control_is_reproducible_and_unique():
 a=matched_random_control(['a','b','c','d'],2,'g4'); b=matched_random_control(['d','c','b','a'],2,'g4')
 assert a==b and len(set(a))==2

def test_epoch_hash_changes_with_semantics():
 assert epoch_fingerprint({'fitness':'v1','sensor':'v1'}) != epoch_fingerprint({'fitness':'v2','sensor':'v1'})

def test_negative_expectancy_cannot_breed_on_relative_rank_alone():
 assert not absolute_viability(-.001,0)
 assert absolute_viability(.001,0)

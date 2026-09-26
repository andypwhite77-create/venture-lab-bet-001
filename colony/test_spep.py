from colony.spep import event_id,twins,panel_manifest

def test_event_id_is_deterministic_and_versioned():
 r={'id':1,'created_at':'2026-01-01T00:00:00Z','mint':'x'}
 assert event_id(r)==event_id(r) and event_id(r).startswith('spep_')
def test_twins_preserve_abstention():
 assert set(twins('abstain','e','g').values())=={'abstain'}
def test_mirror_and_random_are_deterministic():
 a=twins('buy','e','g');b=twins('buy','e','g');assert a==b and a['mirror']=='sell' and a['random_direction'] in ('buy','sell')
def test_manifest_hash_stable():
 p=[{'family':'x','parameters':{'a':1}}]; assert panel_manifest(p)==panel_manifest(p)

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
from colony.spep_value import marginal_value,participation_action,path_step

def test_marginal_buy_sell_abstain_and_friction():
 assert marginal_value(10,'buy',1)==9
 assert marginal_value(10,'sell',1)==-11
 assert marginal_value(10,'abstain',99)==0

def test_participation_control_preserves_participation_not_direction():
 a=participation_action('e','g',True);assert a in ('buy','sell') and a==participation_action('e','g',True)
 assert participation_action('e','g',False)=='abstain'

def test_path_step_preserves_stateful_cash():
 cash,pos=path_step(100,0,10,True,.5);assert cash==105 and pos==0
 cash2,_=path_step(cash,0,-10,True,.5);assert round(cash2,6)==99.75

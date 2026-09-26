from datetime import datetime, timedelta, timezone
from evolve import load_seeds
from forward import eligible, population_hash

def row(t):
    return {"created_at":t,"features":{},"market":{"price_change_m5":-12,"buys_m5":7,"sells_m5":3}}

def test_hash_freezes_population():
    p=load_seeds(); a=population_hash(p)
    p[0]["parameters"]["cooldown_minutes"]=10
    assert population_hash(p) != a

def test_cooldown_blocks_reentry():
    g=load_seeds()[0]; g["parameters"]["cooldown_minutes"]=60
    t=datetime.now(timezone.utc)
    assert eligible(g,row(t),None)
    assert not eligible(g,row(t+timedelta(minutes=30)),t)
    assert eligible(g,row(t+timedelta(minutes=61)),t)

if __name__=='__main__':
    test_hash_freezes_population(); test_cooldown_blocks_reentry(); print('forward tests: PASS')

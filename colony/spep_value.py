"""Pure SPEP policy valuation. No database or market I/O."""
import hashlib,random

def directional_return(raw_return_pct, action):
    r=float(raw_return_pct)
    if action=='buy': return r
    if action=='sell': return -r
    return 0.0

def marginal_value(raw_return_pct,action,friction_pct=0.0):
    if action=='abstain': return 0.0
    return directional_return(raw_return_pct,action)-float(friction_pct)

def participation_action(event_id,genome_id,participates):
    if not participates:return 'abstain'
    seed=int(hashlib.sha256(f'{event_id}|{genome_id}|participation-control-v1'.encode()).hexdigest()[:16],16)
    return random.Random(seed).choice(('buy','sell'))

def path_step(cash,position_value,net_return_pct,participates,allocation=1.0):
    if not participates:return float(cash),float(position_value)
    stake=max(0.0,float(cash))*min(1.0,max(0.0,float(allocation)))
    end=stake*(1+float(net_return_pct)/100.0)
    return float(cash)-stake+end,0.0

"""Environmental niches allow specialist lineages to coexist."""
NICHES=('new_launch','thin_liquidity','high_momentum','wallet_follow','risk_off','generalist')

def classify(features):
    age=features.get('age_minutes'); liq=features.get('liquidity_usd'); mom=features.get('momentum_pct'); wallet=features.get('wallet_signal',0); market=features.get('market_momentum_pct',0)
    tags=[]
    if age is not None and age<=30: tags.append('new_launch')
    if liq is not None and liq<50000: tags.append('thin_liquidity')
    if mom is not None and mom>=10: tags.append('high_momentum')
    if wallet>=.7: tags.append('wallet_follow')
    if market<=-5: tags.append('risk_off')
    return tags or ['generalist']

def niche_fitness(outcomes):
    buckets={}
    for o in outcomes:
        for n in o.get('niches',['generalist']): buckets.setdefault(n,[]).append(float(o['return_pct']))
    return {n:{'n':len(v),'mean_return_pct':round(sum(v)/len(v),4)} for n,v in buckets.items()}

def specialist_bonus(global_rank,niche_rank,niche_n,min_n=10):
    if niche_n<min_n:return 0.0
    return round(max(0.0,global_rank-niche_rank),4)

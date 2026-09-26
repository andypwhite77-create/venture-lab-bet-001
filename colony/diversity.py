"""Frequency-dependent selection: success helps, monoculture hurts."""
from collections import Counter

def family_shares(genomes):
    counts=Counter(g.get('family','unknown') for g in genomes); n=max(1,len(genomes))
    return {k:v/n for k,v in counts.items()}

def diversity_multiplier(family_share,soft_cap=.25,hard_cap=.50):
    if family_share<=soft_cap:return 1.0
    if family_share>=hard_cap:return 0.1
    x=(family_share-soft_cap)/(hard_cap-soft_cap)
    return round(1.0-.9*x,4)

def adjusted_reproductive_access(base_access,family_share):
    return round(base_access*diversity_multiplier(family_share),4)

def protected_family(family_share,min_share=.03):
    return family_share<min_share

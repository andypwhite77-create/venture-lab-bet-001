"""Evidence gates for proposed colony changes. No live mutation happens here."""
MIN_INDEPENDENT_MINTS=30
MIN_EDGE_PCT=5.0
MIN_SCOUT_MINTS=10

def assess(core,sceptic):
    evidence=int(core.get('comparison_evidence_mints',0)); edge=float(core.get('evolved_minus_blind_pct',0))
    objections=list(sceptic.get('objections',[]))
    return {'eligible_for_generation_change': evidence>=MIN_INDEPENDENT_MINTS and edge>=MIN_EDGE_PCT and not objections,
            'eligible_for_scout_proposal': evidence>=MIN_SCOUT_MINTS,
            'thresholds':{'independent_mints':MIN_INDEPENDENT_MINTS,'edge_pct':MIN_EDGE_PCT,'scout_mints':MIN_SCOUT_MINTS},
            'current':{'independent_mints':evidence,'edge_pct':edge,'objections':objections}}

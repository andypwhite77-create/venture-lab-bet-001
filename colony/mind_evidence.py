"""Evidence IDs prevent Mind from relabelling database facts."""
def packet(facts):
    out=[]
    for i,(kind,value) in enumerate(facts,1):
        out.append({'evidence_id':f'E{i:03d}','status':'known','kind':kind,'value':value})
    return out

def validate_claim_refs(payload,valid_ids):
    claims=payload.get('claims',[]) or []
    if not isinstance(claims,list): return False,'claims_not_list'
    for c in claims:
        if not isinstance(c,dict): return False,'bad_claim'
        refs=c.get('evidence_ids',[])
        if any(r not in valid_ids for r in refs): return False,'unknown_evidence_id'
        if c.get('status') not in ('inferred','speculative'): return False,'fact_status_reserved'
    return True,'ok'

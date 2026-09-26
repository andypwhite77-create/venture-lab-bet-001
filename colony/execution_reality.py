"""Counterfactual execution economics using read-only Jupiter quotes. Never signs/broadcasts."""
from colony.jupiter_quotes import quote,SOL
LAMPORTS=1_000_000_000
SIZES_SOL=(.005,.01,.02,.05,.1)
def roundtrip(token_mint,entry_quote,notional_sol):
    """Mark a hypothetical SOL->token->SOL round trip at current executable quotes."""
    try:
        token_units=int(entry_quote.get('out_amount') or 0)
        if token_units<=0:return {'ok':False,'reason':'missing_entry_quote'}
        exitq=quote(token_mint,SOL,token_units,100)
        returned=int(exitq['out_amount'])/LAMPORTS
        gross=returned-float(notional_sol)
        return {'ok':True,'notional_sol':float(notional_sol),'returned_sol':returned,
          'gross_edge_sol':gross,'gross_edge_pct':100*gross/float(notional_sol),
          'entry_price_impact_pct':entry_quote.get('price_impact_pct'),
          'exit_price_impact_pct':exitq.get('price_impact_pct'),'exit_quote':exitq}
    except Exception as exc:return {'ok':False,'reason':type(exc).__name__}
def capacity_curve(token_mint):
    out=[]
    for n in SIZES_SOL:
        try:q=quote(SOL,token_mint,int(n*LAMPORTS),100);out.append(roundtrip(token_mint,q,n))
        except Exception as exc:out.append({'ok':False,'notional_sol':n,'reason':type(exc).__name__})
    return out

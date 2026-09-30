"""Historical-safe context and specialist-council signals for Queen breeding.

Only information available at observation time is exposed. Spartan/holdout outcomes are never read.
"""
from __future__ import annotations
import bisect, math, statistics
from collections import defaultdict


def archetype_signals(obs: dict) -> dict:
    def n(k, d=0.0):
        try: return float(obs.get(k, d) or d)
        except Exception: return float(d)
    pc5=n('price_change_m5'); h1=n('price_change_h1'); br=n('dex_buy_ratio_m5')
    vl=n('volume_liquidity_m5'); acc=n('buy_acceleration'); liq=n('liquidity_usd')
    sig={
      'advisor_reversal': float(pc5 <= -8 and br >= .62),
      'advisor_momentum': float(pc5 >= 5 and vl >= .04),
      'advisor_order_flow': float(br >= .80 and acc >= 1.5),
      'advisor_exhaustion': float(h1 >= 6 and pc5 <= 4 and br <= .72 and vl >= .005),
      'advisor_mean_reversion': float(pc5 <= -2 and h1 <= 8 and liq >= 50000 and br >= .45),
    }
    sig['advisor_count']=sum(sig.values())
    return sig


async def live_specialist_votes(conn) -> dict[int, dict]:
    """Actual prospective specialist firings, keyed by candidate_id."""
    votes=defaultdict(lambda: defaultdict(int))
    try:
        rows=await conn.fetch('''SELECT e.candidate_id,r.family,e.genome_id
          FROM family_tournament_entries e JOIN family_tournament_runs r ON r.run_id=e.run_id''')
        for r in rows: votes[int(r['candidate_id'])][str(r['family'])]+=1
        rows=await conn.fetch('''SELECT e.candidate_id,e.genome_id FROM reversal_tournament_entries e''')
        for r in rows: votes[int(r['candidate_id'])]['reversal']+=1
    except Exception:
        return {}
    out={}
    fams=('reversal','exhaustion','momentum','order_flow','wallet_convergence','mean_reversion')
    for cid,v in votes.items():
        z={f'live_signal_{f}':float(v.get(f,0)>0) for f in fams}
        z.update({f'live_votes_{f}':float(v.get(f,0)) for f in fams})
        z['live_signal_count']=sum(z[f'live_signal_{f}'] for f in fams)
        z['live_council_available']=1.0
        out[cid]=z
    return out


async def enrich_historical_context(conn, rows: list[dict]) -> int:
    """Attach past-only OHLCV regime context from the local historical bank."""
    pairs={str(r.get('flat',{}).get('pair_address')) for r in rows if r.get('flat',{}).get('pair_address')}
    if not pairs: return 0
    try:
        bars=await conn.fetch('''SELECT pair_address,ts,close,volume_usd FROM historical_ohlcv
          WHERE timeframe='1h' AND pair_address = ANY($1::text[]) ORDER BY pair_address,ts''',list(pairs))
    except Exception:
        return 0
    bank=defaultdict(list)
    for b in bars: bank[str(b['pair_address'])].append((b['ts'],float(b['close']),float(b['volume_usd'] or 0)))
    enriched=0
    for r in rows:
        f=r.get('flat',{}); arr=bank.get(str(f.get('pair_address')))
        if not arr: continue
        ts=r.get('created_at'); times=[x[0] for x in arr]; i=bisect.bisect_right(times,ts)-1
        if i<0: continue
        recent=arr[max(0,i-167):i+1]; c=arr[i][1]
        f['hist_context_available']=1.0; enriched+=1
        if i>=24 and arr[i-24][1]: f['hist_return_24h']=(c/arr[i-24][1]-1)*100
        if i>=168 and arr[i-168][1]: f['hist_return_7d']=(c/arr[i-168][1]-1)*100
        closes=[x[1] for x in arr[max(0,i-24):i+1] if x[1]>0]
        rets=[(closes[j]/closes[j-1]-1)*100 for j in range(1,len(closes)) if closes[j-1]>0]
        if len(rets)>=3: f['hist_volatility_24h']=statistics.pstdev(rets)
        v1=sum(x[2] for x in arr[max(0,i-23):i+1]); v0=sum(x[2] for x in arr[max(0,i-47):max(0,i-23)])
        if v0>0: f['hist_volume_ratio_24h']=v1/v0
        cs=[x[1] for x in recent if x[1]>0]
        if cs:
            hi=max(cs); lo=min(cs)
            f['hist_drawdown_7d_pct']=(c/hi-1)*100 if hi else 0.0
            f['hist_position_7d']=(c-lo)/(hi-lo) if hi>lo else .5
    return enriched

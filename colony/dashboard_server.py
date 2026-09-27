from html import escape

def _f(x,d=4):
    try:return f'{float(x):.{d}f}'
    except:return '—'

def _svg(curve):
    vals=[];s=0.0
    for x in curve:
        try:s+=float(x.get('net_pnl') or 0);vals.append(s)
        except:pass
    if not vals:return "<div class='muted'>Waiting for marked colony bets…</div>"
    lo=min(0,*vals);hi=max(0,*vals);span=hi-lo or 1
    pts=[]
    for i,v in enumerate(vals):
        x=10+(i/max(1,len(vals)-1))*580;y=190-((v-lo)/span)*170
        pts.append(f'{x:.1f},{y:.1f}')
    return f"<svg viewBox='0 0 600 210' width='100%' height='220'><polyline fill='none' stroke='currentColor' stroke-width='3' points='{' '.join(pts)}'/></svg>"

def render(j):
    n=j['native'];s=n['summary'];curve=n['curve'];marked=len(curve);wins=sum(1 for x in curve if float(x.get('net_pnl') or 0)>0)
    rate=j.get('sol_gbp');net=float(s.get('net_pnl') or 0);gbp='' if rate is None else f' • £{net*float(rate):.2f}'
    ants=sum(int(x.get('n') or 0) for x in j.get('genomes',[]));real=sum(bool(x.get('broadcast')) for x in n.get('trades',[]))+sum(bool(x.get('broadcast')) for x in j['external'].get('trades',[]))
    cards=[('COLONY BETS',s.get('n',0)),('MARKED',marked),('WIN RATE',f'{wins/marked*100:.1f}%' if marked else '—'),('COLONY NET',f'{net:.6f} SOL{gbp}'),('ANTS',ants),('REAL TX',real)]
    cards_html=''.join(f"<div class=card><div class=muted>{escape(str(k))}</div><div class=num>{escape(str(v))}</div></div>" for k,v in cards)
    fam=''.join(f"<div class=card style='margin:6px 0'><b>{escape(str(x.get('family') or 'unknown'))}</b> • {x.get('trades',0)} bets • {x.get('wins',0)} wins<br><span class={'pos' if float(x.get('net') or 0)>=0 else 'neg'}>net {_f(x.get('net'),6)} SOL{'' if x.get('net_gbp') is None else ' • £'+_f(x.get('net_gbp'),2)}</span></div>" for x in j.get('family_performance',[])) or 'Awaiting marks'
    pop=''.join(f"<div><span class=pill>{escape(str(x.get('family')))}</span> <b>{x.get('n',0)}</b> genomes</div>" for x in j.get('genomes',[]))
    es=j.get('selection') or {}; evo=f"<div class=card style='margin:6px 0'><b>{escape(str(es.get('mode','—')))}</b><br>Evidence gate: <b>{escape(str(es.get('qualify_n','—')))}</b> distinct assets minimum<br>Effective evidence: <b>{escape(str(es.get('effective_evidence_model','—')))}</b><br>Qualified: <b>{es.get('qualified',0)}</b> • Breeding eligible: <b>{es.get('breeding_eligible',0)}</b></div>"
    rows=''.join(_trade_row(x,True) for x in n.get('trades',[]))
    ext=''.join(_trade_row(x,False) for x in j['external'].get('trades',[]))
    mind=''.join(f"<div class=card style='margin:6px 0'><b>{escape(str(x.get('status')))}</b><br><small>{escape(str(x.get('core')))[:260]}</small></div>" for x in j.get('mind',[])) or 'Queen is quiet'
    signals=''.join(f"<div><b>#{x.get('id')}</b> {escape(str(x.get('direction')))} {escape(str(x.get('mint','')))[:8]}…</div>" for x in j.get('signals',[]))
    experiments=''.join(f"<div><span class=pill>{escape(str(x.get('experiment_type')))}</span> {escape(str(x.get('status')))}</div>" for x in j.get('experiments',[])) or 'None'
    events=''.join(f"<div><b>{escape(str(x.get('event_type')))}</b></div>" for x in j.get('events',[]))
    cs=j.get('capital_shadow') or {}; fc=cs.get('family_counts') or {}
    famcounts=' • '.join(f"{escape(str(k))}: {v}" for k,v in sorted(fc.items())) or '—'
    roster=''.join(f"<tr><td>{r.get('rank')}</td><td>{escape(str(r.get('family')))}</td><td>{escape(str(r.get('genome_id')))[:12]}…</td><td>{_f(r.get('fitness'),3)}</td><td>{r.get('evidence_n')}</td><td>{escape(str(r.get('slot_source')))}</td></tr>" for r in cs.get('roster',[]))
    capital=f"<div class=grid><div class=card><div class=muted>SHADOW SLOTS</div><div class=num>{cs.get('active_slots',0)}</div></div><div class=card><div class=muted>EARNED SLOTS</div><div class=num>{cs.get('earned_slots',0)}</div></div><div class=card><div class=muted>GROWTH RESERVE</div><div class=num>£{_f(cs.get('growth_reserve_gbp'),2)}</div></div><div class=card><div class=muted>LOCKED PROFIT</div><div class=num>£{_f(cs.get('locked_profit_gbp'),2)}</div></div></div><p class=muted>Simulation only • £{_f(cs.get('starter_gbp'),2)} starter-risk unit • {int(float(cs.get('growth_share',0))*100)}% of realised profit to growth • family cap {int(float(cs.get('max_family_fraction',0))*100)}% • {famcounts}</p><div class=scroll><table><thead><tr><th>#</th><th>Family</th><th>Genome</th><th>Fitness</th><th>Evidence</th><th>Slot</th></tr></thead><tbody>{roster}</tbody></table></div>"
    return cards_html,_svg(curve),fam,pop,evo,rows,mind,signals,experiments,events,ext,capital

def _trade_row(x,native):
    a=x.get('attribution') or {};family=escape(str(a.get('family','—'))) if native else ''
    ants=a.get('ants','—') if native else ''
    mint=escape(str(x.get('mint','')))[:8]+'…';status=escape(str(x.get('status','')));net=float(x.get('net_pnl') or 0)
    base=f"<td>{family}</td><td>{ants}</td>" if native else ''
    return f"<tr>{base}<td>{mint}</td><td>{status}</td><td class={'pos' if net>=0 else 'neg'}>{net:.6f}</td><td>{_f(x.get('executable_edge_sol'),6)}</td><td>{'—' if x.get('friction_ratio') is None else _f(float(x.get('friction_ratio'))*100,2)+'%'}</td></tr>"

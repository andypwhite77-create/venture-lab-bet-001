from html import escape
import statistics

def _f(x,d=4):
    try:return f'{float(x):.{d}f}'
    except:return '—'

def _label(f):
    return str(f or 'unknown').replace('_',' ').title()

def _bloodline_cards(j):
    perf={x.get('family') or 'unknown':x for x in j.get('family_performance',[])}
    roster={x.get('family'):x for x in j.get('elite_roster',[])}
    ants=(j.get('selection') or {}).get('ants',[])
    names=['reversal','momentum','order_flow','wallet_convergence']
    cards=[]
    for fam in names:
        aa=[a for a in ants if a.get('family')==fam]
        mature=[a for a in aa if int(a.get('n') or 0)>=20 and a.get('avg_return_pct') is not None]
        returns=[float(a['avg_return_pct']) for a in mature]
        pf=perf.get(fam,{})
        r=roster.get(fam,{})
        trades=int(pf.get('trades') or 0);wins=int(pf.get('wins') or 0);net=float(pf.get('net') or 0)
        wr=(wins/trades*100) if trades else None
        rate=j.get('sol_gbp'); net_gbp=(net*float(rate)) if rate is not None else None
        active=int(r.get('active') or 0);elites=int(r.get('elites') or 0);controls=int(r.get('controls') or 0);chall=int(r.get('challengers') or 0)
        state='ELITE FIELD' if elites else 'SEARCHING'
        statecls='good' if elites else 'searching'
        cards.append(f"""<article class='bloodline'>
          <div class='bloodline-head'><div><span class='family-dot {fam}'></span><b>{escape(_label(fam))}</b></div><span class='state {statecls}'>{state}</span></div>
          <div class='bloodline-number'>{active}</div><div class='bloodline-caption'>active prospective ants</div>
          <div class='mini-grid'><div><strong>{elites}</strong><span>elite</span></div><div><strong>{controls}</strong><span>control</span></div><div><strong>{chall}</strong><span>waiting</span></div></div>
          <div class='bloodline-meta'>Stage <b>{r.get('stage_size','—')}</b> • evidence-ready <b>{len(mature)}</b> • mature median <b>{_f(statistics.median(returns) if returns else None,2)}%</b></div>
          <div class='bloodline-meta'>Paper bets <b>{trades}</b> • win rate <b>{_f(wr,1)}%</b> • net <b class={'pos' if net>=0 else 'neg'}>{'£'+_f(net_gbp,2) if net_gbp is not None else '—'}</b> <span class='muted'>• {_f(net,6)} SOL</span></div>
        </article>""")
    return ''.join(cards)

def _svg(curve):
    vals=[];s=0.0
    for x in curve:
        try:s+=float(x.get('net_pnl') or 0);vals.append(s)
        except:pass
    if not vals:return "<div class='empty-chart'>Waiting for marked colony bets…</div>"
    lo=min(0,*vals);hi=max(0,*vals);span=hi-lo or 1;pts=[]
    for i,v in enumerate(vals):
        x=12+(i/max(1,len(vals)-1))*576;y=188-((v-lo)/span)*164;pts.append(f'{x:.1f},{y:.1f}')
    end='goodline' if vals[-1]>=0 else 'badline'
    return f"<svg viewBox='0 0 600 210' width='100%' height='220' class='equity'><line x1='10' y1='188' x2='590' y2='188' class='axis'/><polyline class='{end}' fill='none' stroke-width='4' stroke-linecap='round' stroke-linejoin='round' points='{' '.join(pts)}'/></svg>"

def render(j):
    n=j['native'];s=n['summary'];curve=n['curve'];marked=len(curve);wins=sum(1 for x in curve if float(x.get('net_pnl') or 0)>0)
    rate=j.get('sol_gbp');net=float(s.get('net_pnl') or 0);gbp='' if rate is None else f'£{net*float(rate):.2f}'
    roster=j.get('elite_roster',[]);active=sum(int(x.get('active') or 0) for x in roster);elites=sum(int(x.get('elites') or 0) for x in roster);chall=sum(int(x.get('challengers') or 0) for x in roster)
    real=sum(bool(x.get('broadcast')) for x in n.get('trades',[]))+sum(bool(x.get('broadcast')) for x in j['external'].get('trades',[]))
    acc=j.get('accelerator') or {};left=max(0,int(acc.get('trigger_at',25))-int(acc.get('new_mints',0)))
    cards=[('ACTIVE ANTS',active,'prospective roster'),('QUALIFIED ELITES',elites,'earned training seats'),('CHALLENGERS',chall,'waiting for a seat'),('MARKED BETS',marked,'prospective outcomes'),('COLONY NET',gbp or '—',f'{net:.6f} SOL' if rate is not None else 'paper only'),('NEXT EVOLUTION',f'{left} mints','until accelerator sweep')]
    cards_html=''.join(f"<div class='metric'><div class='metric-label'>{escape(k)}</div><div class='metric-value'>{escape(str(v))}</div><div class='metric-note'>{escape(str(note))}</div></div>" for k,v,note in cards)
    fam=_bloodline_cards(j)
    pop=''.join(f"<div class='roster-row'><span><span class='family-dot {x.get('family')}'></span>{escape(_label(x.get('family')))}</span><span><b>{x.get('active',0)}</b> active &nbsp; <b>{x.get('elites',0)}</b> elite &nbsp; <b>{x.get('challengers',0)}</b> queued</span></div>" for x in roster)
    es=j.get('selection') or {};newm=int(acc.get('new_mints',0));trigger=int(acc.get('trigger_at',25));pct=min(100,(newm/trigger*100) if trigger else 0)
    evo=f"""<div class='gate'><div class='gate-head'><b>Evolution engine</b><span class='state good'>RUNNING</span></div>
      <div class='progress'><i style='width:{pct:.1f}%'></i></div><div class='gate-copy'><b>{newm}/{trigger}</b> new independent mints toward next mass sweep</div>
      <div class='gate-stats'><span>Prospective gate <b>{escape(str(es.get('qualify_n','—')))}</b></span><span>Qualified <b>{es.get('qualified',0)}</b></span><span>Breeding eligible <b>{es.get('breeding_eligible',0)}</b></span></div>
      <small>Historical compute discovers candidates. Only future evidence decides whether they deserve to stay.</small></div>"""
    bio=j.get('biology') or {}; drv=j.get('drives') or {};fd=(drv.get('drives') or {}).get('fission') or {}
    evo+=f"<div class='gate compact'><b>Authority boundary</b><div class='authority'><span>Paper/shadow <b class=pos>ON</b></span><span>Real-money authority <b class=neg>OFF</b></span><span>Fission progress <b>{_f(float(fd.get('progress_fraction') or 0)*100,4)}%</b></span></div></div>"
    sm=j.get('stake_model') or {}; evo+=f"<div class='gate compact'><b>Stake economics</b><div class='authority'><span>Per-ant paper stake <b>£{_f(sm.get('stake_gbp'),2)}</b></span><span>Measured round-trip network cost <b>£{_f(sm.get('roundtrip_network_fee_gbp'),4)}</b></span><span>Fixed-cost drag <b>{_f(sm.get('fixed_fee_pct_at_stake'),4)}%</b></span></div><small>Fitness now evaluates fixed execution costs at the intended canary stake. Percentage edge and £ profitability are tracked separately so a good signal is not killed merely because a toy stake cannot absorb fixed fees.</small></div>"
    rows=''.join(_trade_row(x,True) for x in n.get('trades',[]));ext=''.join(_trade_row(x,False) for x in j['external'].get('trades',[]))
    mind=''.join(f"<div class='feed-item'><div><b>{escape(str(x.get('status')))}</b><span class=feed-time>{escape(str(x.get('observed_at','')))[:19]}</span></div><small>{escape(str(x.get('core')))[:260]}</small></div>" for x in j.get('mind',[])) or "<div class=empty>Queen is quiet</div>"
    signals=''.join(f"<div class='feed-item'><b>#{x.get('id')}</b> {escape(str(x.get('direction')))} <code>{escape(str(x.get('mint','')))[:8]}…</code></div>" for x in j.get('signals',[])) or '<div class=empty>None</div>'
    experiments=''.join(f"<div class='feed-item'><span class=pill>{escape(str(x.get('experiment_type')))}</span> {escape(str(x.get('status')))}</div>" for x in j.get('experiments',[])) or '<div class=empty>None</div>'
    scouts=j.get('queen_scouts') or []
    if scouts: experiments += ''.join(f"<div class='feed-item'>🐜 <b>{escape(str(x.get('state')))}</b> • n={x.get('evidence_n',0)} • mean={_f(x.get('mean_return_pct'),2)}%</div>" for x in scouts)
    events=''.join(f"<div class='feed-item'><b>{escape(str(x.get('event_type')))}</b></div>" for x in j.get('events',[])) or '<div class=empty>None</div>'
    cs=j.get('capital_shadow') or {};fc=cs.get('family_counts') or {};famcounts=' • '.join(f"{escape(_label(k))}: {v}" for k,v in sorted(fc.items())) or '—'
    rost=''.join(f"<tr><td>{r.get('rank')}</td><td>{escape(_label(r.get('family')))}</td><td><code>{escape(str(r.get('genome_id')))[:12]}…</code></td><td>{_f(r.get('fitness'),3)}</td><td>{r.get('evidence_n')}</td><td>{escape(str(r.get('slot_source')))}</td></tr>" for r in cs.get('roster',[]))
    capital=f"<div class='submetrics'><div><span>Shadow slots</span><b>{cs.get('active_slots',0)}</b></div><div><span>Earned slots</span><b>{cs.get('earned_slots',0)}</b></div><div><span>Growth reserve</span><b>£{_f(cs.get('growth_reserve_gbp'),2)}</b></div><div><span>Locked profit</span><b>£{_f(cs.get('locked_profit_gbp'),2)}</b></div></div><p class=muted>{famcounts}</p><div class=scroll><table><thead><tr><th>#</th><th>Family</th><th>Genome</th><th>Fitness</th><th>Evidence</th><th>Slot</th></tr></thead><tbody>{rost}</tbody></table></div>"
    return cards_html,_svg(curve),fam,pop,evo,rows,mind,signals,experiments,events,ext,capital

def _trade_row(x,native):
    a=x.get('attribution') or {};family=escape(_label(a.get('family','—'))) if native else '';ants=a.get('ants','—') if native else ''
    mint=escape(str(x.get('mint','')))[:8]+'…';status=escape(str(x.get('status','')));net=float(x.get('net_pnl') or 0);base=f"<td>{family}</td><td>{ants}</td>" if native else ''
    return f"<tr>{base}<td><code>{mint}</code></td><td>{status}</td><td class={'pos' if net>=0 else 'neg'}>{net:.6f}</td><td>{_f(x.get('executable_edge_sol'),6)}</td><td>{'—' if x.get('friction_ratio') is None else _f(float(x.get('friction_ratio'))*100,2)+'%'}</td></tr>"

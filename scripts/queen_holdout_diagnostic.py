import asyncio, json, statistics
from db import connection, init_db
from colony.historical_nursery import load_rows, split_rows
from colony.evaluator import matches
from colony.paper_economics import TARGET_STAKE_GBP, measured_roundtrip_network_fee_sol, sol_gbp_rate, adjusted_return_pct

def bucket_liq(v):
    v=float(v or 0)
    if v<25000:return '<25k'
    if v<50000:return '25-50k'
    if v<100000:return '50-100k'
    return '>=100k'

def bucket_age(v):
    v=float(v or 0)
    if v<6:return '<6h'
    if v<24:return '6-24h'
    if v<168:return '1-7d'
    return '>=7d'

def regime(r):
    f=r['flat']; h=float(f.get('price_change_h1',0) or 0); a=float(f.get('volume_liquidity_m5',0) or 0)
    if h<=-8:return 'selloff'
    if h>=8:return 'surge'
    if a>=.15:return 'high_activity'
    return 'chop'

def mean(xs): return statistics.fmean(xs) if xs else None
def obs_for(g, rows, fixed):
    out=[]; seen=set(); hold=int(g.get('parameters',{}).get('hold_minutes',15))
    for r in rows:
        if r['mint'] in seen or not matches(g,r['flat']): continue
        ret=r['returns'].get(hold)
        if ret is None and r['returns']:
            h=min(r['returns'],key=lambda x:abs(x-hold)); ret=r['returns'][h]
        if ret is None: continue
        ret=float(ret)
        sl=g.get('parameters',{}).get('stop_loss_pct'); tp=g.get('parameters',{}).get('take_profit_pct')
        if sl is not None and ret<=float(sl): ret=float(sl)
        if tp is not None and ret>=float(tp): ret=float(tp)
        out.append((r,ret,adjusted_return_pct(ret,TARGET_STAKE_GBP,fixed)))
        seen.add(r['mint'])
    return out

def summarize(vals):
    if not vals:return {'n':0}
    raw=[x[1] for x in vals]; net=[x[2] for x in vals]
    return {'n':len(vals),'raw_mean_pct':mean(raw),'net_mean_pct':mean(net),
            'net_mean_gbp':mean(net)*TARGET_STAKE_GBP/100,
            'win_rate':sum(x>0 for x in net)/len(net),
            'best_net_pct':max(net),'worst_net_pct':min(net)}

async def main():
    await init_db()
    async with connection() as c:
        rec=await c.fetchrow("SELECT id,created_at,finalists FROM historical_nursery_runs WHERE family='queen_pattern' ORDER BY created_at DESC LIMIT 1")
        fs=rec['finalists']; fs=json.loads(fs) if isinstance(fs,str) else fs
        rows=await load_rows(c); train,val,hold=split_rows(rows)
        fee=await measured_roundtrip_network_fee_sol(c); rate,src=sol_gbp_rate(); fixed=fee*rate
    print('RUN',rec['id'],rec['created_at'],'finalists',len(fs),'rows',len(rows),
          'split_mints',*[len({r['mint'] for r in s}) for s in (train,val,hold)])
    print('COST stake_gbp',TARGET_STAKE_GBP,'fixed_roundtrip_gbp',fixed,
          'fee_drag_pct',fixed/TARGET_STAKE_GBP*100,'solgbp',rate,src)
    for name,part in [('train',train),('validation',val),('holdout',hold)]:
        allobs=[]
        for x in fs: allobs+=obs_for(x['genome'],part,fixed)
        print('PART',name,json.dumps(summarize(allobs),sort_keys=True))
    by_hold={};by_reg={};by_liq={};by_age={};by_sensor={};genome_hold=[]
    for x in fs:
        g=x['genome']; oo=obs_for(g,hold,fixed)
        hm=int(g.get('parameters',{}).get('hold_minutes',15)); by_hold.setdefault(str(hm),[]).extend(oo)
        genome_hold.append((x['genome_id'],x['holdout'].get('avg_net_gbp'),hm,list(g.get('predicates',{}))))
        for rr,raw,net in oo:
            by_reg.setdefault(regime(rr),[]).append((rr,raw,net))
            by_liq.setdefault(bucket_liq(rr['flat'].get('liquidity_usd')),[]).append((rr,raw,net))
            by_age.setdefault(bucket_age(rr['flat'].get('pair_age_hours')),[]).append((rr,raw,net))
        for sensor in g.get('predicates',{}):
            by_sensor.setdefault(sensor,[]).append(float(x['holdout'].get('avg_net_gbp') or 0))
    for label,d in [('HOLD',by_hold),('REGIME',by_reg),('LIQ',by_liq),('AGE',by_age)]:
        print('---',label)
        for k,v in sorted(d.items()): print(k,json.dumps(summarize(v),sort_keys=True))
    print('--- SENSOR finalist-level holdout GBP')
    for k,v in sorted(by_sensor.items(),key=lambda kv:(mean(kv[1]) if kv[1] else 999)):
        if len(v)>=3: print(k,'n_genomes',len(v),'mean_gbp',round(mean(v),4),'best_gbp',round(max(v),4))
    print('--- BEST FINALISTS')
    for gid,hg,hm,sens in sorted(genome_hold,key=lambda x:(x[1] if x[1] is not None else -999),reverse=True)[:10]:
        print(gid,'holdout_gbp',hg,'hold',hm,'sensors',','.join(sens))

asyncio.run(main())

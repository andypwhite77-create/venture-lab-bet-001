"""Read-only capital-preservation challenger.

Counterfactual from pre-entry features and *subsequently measured* outcome;
never becomes an execution veto and cannot alter live or Spartan authority.
"""
import asyncio,json
from db import init_db,connection

RULE_VERSION='capital_preservation_shadow_v1'
def classify(market):
    liquidity=float(market.get('liquidity_usd') or 0)
    m5=float(market.get('price_change_m5') or 0)
    h1=float(market.get('price_change_h1') or 0)
    age=market.get('pair_created_at')
    reasons=[]
    if liquidity<75000:reasons.append('liquidity_below_75k')
    if m5<=-12:reasons.append('falling_over_12pct_5m')
    if h1<=-25:reasons.append('falling_over_25pct_1h')
    return reasons

async def evaluate():
    await init_db()
    async with connection() as c:
        await c.execute("""CREATE TABLE IF NOT EXISTS capital_preservation_shadow_runs (
          id BIGSERIAL PRIMARY KEY,run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          version TEXT NOT NULL, sample_n INTEGER NOT NULL,
          results JSONB NOT NULL)""")
        rows=await c.fetch("""SELECT i.id,i.candidate_id,i.status,i.reason,c.market,
          o.net_return_pct
          FROM canary_trade_intents i
          JOIN research_candidates c ON c.id=i.candidate_id
          LEFT JOIN research_outcomes o ON o.candidate_id=i.candidate_id AND o.horizon_minutes=i.hold_minutes
          WHERE i.observed_at >= now()-interval '30 days'
          ORDER BY i.id DESC LIMIT 500""")
        groups={'pass':[],'veto':[]}
        for r in rows:
            if r['net_return_pct'] is None:continue
            market=r['market'];market=json.loads(market) if isinstance(market,str) else (market or {})
            reasons=classify(market)
            groups['veto' if reasons else 'pass'].append(float(r['net_return_pct']))
        result={'version':RULE_VERSION,'scope':'shadow_only_historical_5m_outcomes_not_executable',
                'filters':{'min_liquidity_usd':75000,'m5_decline_veto_pct':-12,'h1_decline_veto_pct':-25},
                'groups':{k:{'n':len(v),'mean_net_return_pct':sum(v)/len(v) if v else None,
                  'wins':sum(x>0 for x in v),'worst_pct':min(v) if v else None} for k,v in groups.items()}}
        await c.execute("INSERT INTO capital_preservation_shadow_runs(version,sample_n,results) VALUES($1,$2,$3::jsonb)",
           RULE_VERSION,sum(len(v) for v in groups.values()),json.dumps(result))
    print(json.dumps(result))
if __name__=='__main__':asyncio.run(evaluate())

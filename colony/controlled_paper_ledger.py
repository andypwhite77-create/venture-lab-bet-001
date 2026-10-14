"""Immutable, observation-only ledger for the five frozen reference ants.

Outcomes are observed research marks, not executable fills. Never authorizes
trading, promotion or breeding. Missing outcomes remain pending.
"""
import asyncio
from db import init_db, connection
from colony.paper_economics import adjusted_return_pct, measured_roundtrip_network_fee_sol, sol_gbp_rate

SCHEMA = """
CREATE TABLE IF NOT EXISTS controlled_paper_trade_ledger (
 entry_id bigint PRIMARY KEY REFERENCES eve_reference_paper_entries(id),
 genome_id text NOT NULL,
 family text NOT NULL,
 mint text NOT NULL,
 entry_at timestamptz NOT NULL,
 horizon_minutes integer NOT NULL,
 outcome_id bigint NOT NULL REFERENCES research_outcomes(id),
 outcome_at timestamptz NOT NULL,
 raw_return_pct double precision NOT NULL,
 assumed_cost_bps double precision NOT NULL,
 fixed_fee_gbp double precision NOT NULL,
 net_return_pct double precision NOT NULL,
 stake_gbp double precision NOT NULL,
 paper_pnl_gbp double precision NOT NULL,
 captured_at timestamptz NOT NULL DEFAULT now(),
 authority text NOT NULL DEFAULT 'observation_only_not_executable'
);
"""
async def run():
 await init_db()
 async with connection() as c:
  await c.execute(SCHEMA)
  fee_sol=await measured_roundtrip_network_fee_sol(c)
  rate,source=sol_gbp_rate()
  fixed=fee_sol*rate
  # Existing outcome returns are treated as raw. Add explicit conservative
  # 100bps round-trip friction; do not trust outcome's precomputed net.
  rows=await c.fetch("""SELECT e.id entry_id,e.genome_id,e.family,e.mint,
    e.observed_at,e.hold_minutes,e.stake_gbp,
    o.id outcome_id,o.measured_at,o.raw_return_pct
    FROM controlled_paper_cohort cohort
    JOIN eve_reference_paper_entries e ON e.genome_id=cohort.genome_id
    JOIN LATERAL (
      SELECT id,measured_at,raw_return_pct FROM research_outcomes
      WHERE candidate_id=e.candidate_id AND horizon_minutes=e.hold_minutes
        AND measured_at>=e.observed_at+e.hold_minutes*interval '1 minute'
        AND raw_return_pct IS NOT NULL
      ORDER BY measured_at ASC,id ASC LIMIT 1
    ) o ON true
    WHERE e.observed_at>=cohort.started_at
      AND cohort.status='observation_only'
      AND NOT EXISTS (SELECT 1 FROM controlled_paper_trade_ledger l WHERE l.entry_id=e.id)
    ORDER BY e.id LIMIT 2000""")
  added=0
  for r in rows:
   stake=float(r['stake_gbp'])
   net=adjusted_return_pct(float(r['raw_return_pct'])-1.0,stake,fixed)
   result=await c.execute("""INSERT INTO controlled_paper_trade_ledger
    (entry_id,genome_id,family,mint,entry_at,horizon_minutes,outcome_id,outcome_at,
     raw_return_pct,assumed_cost_bps,fixed_fee_gbp,net_return_pct,stake_gbp,paper_pnl_gbp)
    VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,100,$10,$11,$12,$13)
    ON CONFLICT DO NOTHING""",r['entry_id'],r['genome_id'],r['family'],r['mint'],
    r['observed_at'],r['hold_minutes'],r['outcome_id'],r['measured_at'],
    float(r['raw_return_pct']),fixed,net,stake,stake*net/100)
   added+=int(result.endswith('1'))
  summary=await c.fetch("""SELECT c.family,count(l.entry_id) completed,
    round(avg(l.net_return_pct)::numeric,3) mean_net_pct,
    round(sum(l.paper_pnl_gbp)::numeric,3) paper_pnl_gbp,
    round(min(l.net_return_pct)::numeric,3) worst_net_pct
    FROM controlled_paper_cohort c LEFT JOIN controlled_paper_trade_ledger l
    ON l.genome_id=c.genome_id GROUP BY c.family ORDER BY c.family""")
  print({'new_marks':added,'fee_rate_source':source,'fixed_fee_gbp':fixed,
    'summary':[dict(x) for x in summary]})
if __name__=='__main__': asyncio.run(run())

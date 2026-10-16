"""Read-only common-wallet replay with duplicate candidate exposure lock."""
import asyncio,json,heapq
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from db import init_db,connection
from colony.plasticity_capital_daily import replay
SQL="""SELECT e.id entry_id,e.genome_id,e.candidate_id,e.observed_at entry_at,e.stake_gbp,d.action,
 l.outcome_at,l.captured_at,l.net_return_pct,
 a.status entry_status,a.latency_seconds entry_latency,
 b.status exit_status,b.latency_seconds exit_latency
 FROM plasticity_forward_decisions d JOIN eve_reference_paper_entries e ON e.id=d.entry_id
 LEFT JOIN controlled_paper_trade_ledger l ON l.entry_id=e.id
 LEFT JOIN canary_forward_quote_observations a ON a.entry_id=e.id AND a.phase='entry'
 LEFT JOIN canary_forward_quote_observations b ON b.entry_id=e.id AND b.phase='exit'
 ORDER BY e.observed_at,e.id"""
def simulate(rows,start_gbp=125,per_trade_gbp=25,friction_pct=1,as_of=None):
 if start_gbp<=0 or per_trade_gbp<=0 or friction_pct<0:raise ValueError('invalid portfolio assumptions')
 as_of=as_of or datetime.now(timezone.utc)
 ordered=sorted((dict(r) for r in rows if r['entry_at']<=as_of),key=lambda r:(r['entry_at'],r['entry_id']))
 result={}
 for arm in ('fixed_dna','plasticity'):
  cash=float(start_gbp);locked=0.;pnl=0.;openq=[];pending=[];seen=set();counts=defaultdict(int);daily=defaultdict(float)
  def release(at):
   nonlocal cash,locked,pnl
   while openq and openq[0][0]<=at:
    atclose,_,candidate,stake,delta=heapq.heappop(openq)
    locked-=stake;cash+=stake+delta;pnl+=delta;seen.discard(candidate)
    daily[atclose.date().isoformat()]+=delta
  for r in ordered:
   release(r['entry_at'])
   if arm=='plasticity' and r['action']!='follow_dna':counts['abstained']+=1;continue
   candidate=r['candidate_id']
   if candidate in seen:counts['duplicate_candidate_blocked']+=1;continue
   if cash<=0.0000001:counts['no_cash']+=1;continue
   stake=min(cash,per_trade_gbp,float(r['stake_gbp']))
   if stake<=0:counts['no_cash']+=1;continue
   cash-=stake;locked+=stake;seen.add(candidate);counts['entered']+=1
   close=r.get('outcome_at');captured=r.get('captured_at');ret=r.get('net_return_pct')
   if close is None or captured is None or ret is None:
    pending.append({'entry_id':r['entry_id'],'candidate_id':candidate,'stake_gbp':round(stake,4),'entry_at':r['entry_at'],'state':'unpriced'});continue
   finish=max(r['entry_at'],close,captured)
   if finish>as_of:
    pending.append({'entry_id':r['entry_id'],'candidate_id':candidate,'stake_gbp':round(stake,4),'entry_at':r['entry_at'],'state':'scheduled_not_closed'});continue
   delta=max(-stake,stake*(float(ret)-friction_pct)/100)
   heapq.heappush(openq,(finish,r['entry_id'],candidate,stake,delta));counts['marked']+=1
  release(as_of)
  for p in pending:
   p['state']='overdue_unpriced' if p['entry_at']+timedelta(minutes=60)<as_of and p['state']=='unpriced' else p['state']
  result[arm]={'cash_gbp':round(cash,3),'locked_gbp':round(locked,3),'closed_pnl_gbp':round(pnl,3),'book_equity_gbp':round(cash+locked,3),
    'accounting_delta_gbp':round(cash+locked-start_gbp-pnl,8),'counts':dict(counts),'daily_closed_pnl_gbp':{k:round(v,3) for k,v in sorted(daily.items())},
    'unresolved':{'pending':len(pending),'overdue':sum(p['state']=='overdue_unpriced' for p in pending),'locked_gbp':round(sum(p['stake_gbp'] for p in pending),3),'positions':[{**p,'entry_at':p['entry_at'].isoformat()} for p in pending]}}
 return {'shared_start_gbp':start_gbp,'stake_cap_gbp':per_trade_gbp,'results':result,
  'authority':'research_only_not_executable','caveat':'Paper marks and candidate deduplication only. Unpriced capital is locked; its liquidation value is unknown.'}
async def run(start_at=None):
 await init_db()
 async with connection() as c:rows=await c.fetch(SQL)
 if start_at:
  # This is a genuinely prospective replay: historical positions remain in
  # the original report but never contaminate the newly funded research wallet.
  rows=[r for r in rows if r['entry_at']>=start_at]
 output=simulate(rows)
 if start_at:output['cohort_started_at']=start_at.isoformat()
 return output
if __name__=='__main__':
 import os
 start=os.getenv('SHARED_WALLET_COHORT_START_UTC')
 start_at=datetime.fromisoformat(start.replace('Z','+00:00')) if start else None
 print(json.dumps(asyncio.run(run(start_at))))

"""Fail-closed cash qualification over immutable quote-derived event evidence.
Legacy unrestricted journal is NOT authoritative. No orders or live authorization.
"""
from collections import defaultdict
START_LAMPORTS=100_000_000

def reconcile(rows):
 grouped=defaultdict(list)
 for raw in rows:grouped[str(raw['genome_id'])].append(dict(raw))
 outcome={}
 for gid,items in grouped.items():
  cash=START_LAMPORTS;reserved={};accepted=set();rejected=[];released=0
  # Chronological order; release at its recorded due time, never before.
  for r in sorted(items,key=lambda x:(x['event_at'],0 if x['action']=='release' else 1,x['source_entry_id'])):
   amount=int(r['amount_lamports']);key=r['source_entry_id']
   if amount<=0:rejected.append((key,'invalid_amount'));continue
   if r['action']=='reserve':
    if key in accepted:rejected.append((key,'duplicate_reservation'));continue
    if cash<amount:rejected.append((key,'insufficient_cash'));continue
    cash-=amount;reserved[key]=amount;accepted.add(key)
   elif r['action']=='release':
    if key not in reserved:rejected.append((key,'unfunded_release'));continue
    del reserved[key];cash+=amount;released+=1
   else:rejected.append((key,'unknown_action'))
  outcome[gid]={'available_lamports':cash,'locked_lamports':sum(reserved.values()),'funded_positions':len(accepted),'released_positions':released,'rejected_events':len(rejected),'authority':'audit_only_no_fills'}
 return outcome

async def run(conn):
 rows=await conn.fetch('SELECT genome_id,source_entry_id,action,amount_lamports,event_at FROM paper_cash_events ORDER BY genome_id,event_at,id')
 return reconcile(rows)

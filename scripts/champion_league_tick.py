#!/usr/bin/env python3
"""One research-only Champion League maintenance tick.

No signer, no wallet access, no broadcast capability. It enrolls the latest Queen top
2, records forward paper opportunities, appends immutable qualification evidence,
refreshes Arena rankings, and applies research-pool promotions only when both
historical and forward evidence beat an Elite incumbent.
"""
import asyncio,json
from db import init_db,connection
from colony.champion_league import seed_founders,enroll_queen_top2,paper_run_once,refresh_rankings
from colony.qualification_corpus import sync as sync_corpus,snapshot as corpus_snapshot
from colony.reliability_lab import enroll as enroll_reliability_lab

async def main():
 await init_db()
 async with connection() as c:
  seed=await seed_founders(c)
  reliability=await enroll_reliability_lab(c)
  r=await c.fetchrow("SELECT id,finalists FROM historical_nursery_runs WHERE family='queen_pattern' ORDER BY created_at DESC LIMIT 1")
  queen=None
  if r:
   fs=r['finalists'];fs=json.loads(fs) if isinstance(fs,str) else list(fs or [])
   queen=await enroll_queen_top2(c,fs,int(r['id']))
  paper=await paper_run_once(c,1000)
  corpus_sync=await sync_corpus(c)
  ranking=await refresh_rankings(c,allow_promotion=True)
  corpus=await corpus_snapshot(c)
 print(json.dumps({'seed':seed,'reliability':reliability,'queen':queen,'paper':paper,'corpus_sync':corpus_sync,'corpus':corpus,'ranking':ranking},default=str,indent=2))

if __name__=='__main__':asyncio.run(main())

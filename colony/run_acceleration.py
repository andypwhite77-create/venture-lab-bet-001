import asyncio,json
from db import init_db,connection
from colony.historical_nursery import FAMILIES,run_family
from colony.pattern_discovery import discover

async def main():
 await init_db()
 async with connection() as c:
  outputs=[]
  for fam in FAMILIES:
   print('NURSERY_START',fam,flush=True)
   r=await run_family(c,fam,50000 if fam=='reversal' else 10000,10)
   finalists=r.pop('finalists')
   await c.execute('''INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary)
      VALUES($1,$2,$3,$4::jsonb,$5::jsonb)''',fam,r['tested'],r['rows'],json.dumps(finalists),json.dumps(r,default=str))
   print('NURSERY_DONE',fam,json.dumps(r,default=str),flush=True)
   outputs.append(r)
  print('PATTERN_START',flush=True)
  p=await discover(c,30)
  for x in p['top']:
   await c.execute('INSERT INTO discovered_patterns(rule,robust_score,evidence) VALUES($1::jsonb,$2,$3::jsonb)',json.dumps(x['rule']),x['robust_score'],json.dumps(x,default=str))
  print('PATTERN_DONE',json.dumps(p,default=str),flush=True)
asyncio.run(main())

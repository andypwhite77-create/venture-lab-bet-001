import asyncio,json
from db import init_db,connection
from colony.queen_pattern_recognition import run
async def main():
 await init_db()
 async with connection() as c:
  s,f=await run(c)
  print('FINAL',json.dumps(s),flush=True)
asyncio.run(main())

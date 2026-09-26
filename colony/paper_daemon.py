"""Autonomous paper loop. No signer, no broadcast capability."""
import asyncio,logging
from db import init_db
from colony.paper_pipeline import run_once
from colony.paper_mark import mark_pending
from colony.native_intents import run_once as native_run_once
log=logging.getLogger('colony.paper')
async def loop(interval=300):
 await init_db()
 while True:
  try:
   trades=await run_once(10)
   native=await native_run_once(20)
   marks_external=await mark_pending('paper-livequote-v1')
   marks_native=await mark_pending('colony-native-v1')
   log.info('paper cycle external=%s native=%s marks_external=%s marks_native=%s',
            len(trades),len(native),len(marks_external),len(marks_native))
  except Exception:log.exception('paper cycle failed')
  await asyncio.sleep(interval)
if __name__=='__main__':
 logging.basicConfig(level=logging.INFO)
 asyncio.run(loop())

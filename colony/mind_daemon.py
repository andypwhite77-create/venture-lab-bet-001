"""Periodic Queen/Sceptic wake cycle on host network for local Ollama access."""
import asyncio, logging
from db import init_db, connection
from colony.mind_cycle import wake

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

async def active_run():
    async with connection() as c:
        return await c.fetchval("""SELECT run_id FROM colony_forward_runs
          WHERE status='collecting' AND frozen_until>now() ORDER BY started_at DESC LIMIT 1""")

async def main(interval=1800):
    await init_db()
    while True:
        try:
            run=await active_run()
            if run:
                result=await wake(run)
                logging.info('queen_cycle %s',result)
            else:
                logging.info('queen_cycle no active run')
        except Exception:
            logging.exception('queen_cycle_error')
        await asyncio.sleep(interval)

if __name__=='__main__': asyncio.run(main())

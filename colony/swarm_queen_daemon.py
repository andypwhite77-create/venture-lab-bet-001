"""Periodic executive-monitor cycle for Swarm Queen."""
import asyncio, logging, os
from db import init_db
from colony.swarm_queen import wake
from colony.swarm_queen_strategy import process_pending
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

async def main(interval=None):
    interval=int(interval or os.getenv('SWARM_QUEEN_INTERVAL_SECONDS','30'))
    await init_db()
    while True:
        try:
            strategic=await process_pending()
            if strategic: logging.info('swarm_strategic %s',strategic)
            logging.info('swarm_queen %s',await wake(executive_inference=False))
        except Exception: logging.exception('swarm_queen_error')
        await asyncio.sleep(interval)

if __name__=='__main__': asyncio.run(main())

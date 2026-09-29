"""Periodic executive-monitor cycle for Swarm Queen."""
import asyncio, logging
from db import init_db
from colony.swarm_queen import wake
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

async def main(interval=900):
    await init_db()
    while True:
        try: logging.info('swarm_queen %s',await wake())
        except Exception: logging.exception('swarm_queen_error')
        await asyncio.sleep(interval)

if __name__=='__main__': asyncio.run(main())

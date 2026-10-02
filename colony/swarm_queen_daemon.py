"""Swarm Queen research-director daemon.

Polls strategic requests and publishes research-safe ecology guidance. It has no genome
creation, promotion, wallet or trading authority.
"""
import asyncio, logging, os, time
from db import init_db
from colony.swarm_queen import wake
from colony.swarm_queen_strategy import process_pending
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

async def main(interval=None):
    wake_interval=int(interval or os.getenv('SWARM_QUEEN_INTERVAL_SECONDS','300'))
    poll_interval=max(2,int(os.getenv('SWARM_STRATEGIC_POLL_SECONDS','5')))
    await init_db(); last_wake=0.0
    while True:
        try:
            strategic=await process_pending()
            if strategic: logging.info('swarm_strategic %s',strategic)
            now=time.time()
            if strategic or now-last_wake>=wake_interval:
                logging.info('swarm_queen %s',await wake(executive_inference=False));last_wake=time.time()
        except Exception:
            logging.exception('swarm_queen_error')
        await asyncio.sleep(poll_interval)

if __name__=='__main__': asyncio.run(main())

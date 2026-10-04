"""Swarm Queen research-director daemon.

Polls strategic requests and publishes research-safe ecology guidance. It has no genome
creation, promotion, wallet or trading authority.
"""
import asyncio, logging, os, time
from db import init_db
from colony.swarm_queen import wake
from colony.swarm_queen_strategy import process_pending
from colony.recovery_assessment import process_pending as process_recovery_assessment
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

async def main(interval=None):
    wake_interval=int(interval or os.getenv('SWARM_QUEEN_INTERVAL_SECONDS','300'))
    poll_interval=max(2,int(os.getenv('SWARM_STRATEGIC_POLL_SECONDS','5')))
    await init_db(); last_wake=0.0; strategic_task=None; recovery_task=None
    while True:
        try:
            # Strategic review is advisory and may be slow. Never let it block the normal Swarm loop.
            if strategic_task is None or strategic_task.done():
                if strategic_task is not None:
                    try:
                        strategic=strategic_task.result()
                        if strategic: logging.info('swarm_strategic %s',strategic)
                    except Exception:
                        logging.exception('swarm_strategic_error')
                strategic_task=asyncio.create_task(process_pending())
            # Recovery assessment is advisory-only and must never block Swarm or strategic review.
            if recovery_task is None or recovery_task.done():
                if recovery_task is not None:
                    try:
                        recovery=recovery_task.result()
                        if recovery: logging.info('swarm_recovery_assessment %s',recovery)
                    except Exception:
                        logging.exception('swarm_recovery_assessment_error')
                recovery_task=asyncio.create_task(process_recovery_assessment())
            now=time.time()
            if now-last_wake>=wake_interval:
                logging.info('swarm_queen %s',await wake(executive_inference=False));last_wake=time.time()
        except Exception:
            logging.exception('swarm_queen_error')
        await asyncio.sleep(poll_interval)

if __name__=='__main__': asyncio.run(main())

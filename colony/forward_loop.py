"""Long-running prospective colony logger."""
import asyncio, logging
from db import init_db
from colony.forward_worker import process
from colony.control_worker import process_controls
from colony.sensory_worker import process_senses
from colony.observer import persist as persist_observer
from colony.proposer import propose
from colony.shadow_orchestrator import cycle as shadow_cycle
from colony.spep_worker import process as process_spep
from colony.spep_mark import mark as mark_spep
from colony.queen_scouts import process as process_queen_scouts

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

async def main():
    await init_db()
    while True:
        try:
            result=await process()
            logging.info('forward_colony %s',result)
            spep=await process_spep(result.get('run')) if result.get('run') else {}
            logging.info('spep %s',spep)
            spep_marks=await mark_spep()
            logging.info('spep_marks %s',spep_marks)
            controls=await process_controls()
            logging.info('control_colonies %s',controls)
            senses=await process_senses()
            logging.info('sensory_memory %s',senses)
            observer=await persist_observer()
            logging.info('observer %s',observer)
            proposal=await propose()
            logging.info('proposal_gate %s',proposal)
            shadow=await shadow_cycle(result.get('run')) if result.get('run') else {}
            logging.info('shadow_ecology %s',shadow)
            queen_scouts=await process_queen_scouts()
            logging.info('queen_scouts %s',queen_scouts)
        except Exception:
            logging.exception('forward_colony_error')
        await asyncio.sleep(60)

if __name__=='__main__': asyncio.run(main())

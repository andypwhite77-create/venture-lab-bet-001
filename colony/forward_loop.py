"""Long-running prospective colony logger with bounded maintenance cadence."""
import asyncio, logging
from db import init_db, connection
from colony.forward_worker import process
from colony.control_worker import process_controls
from colony.sensory_worker import process_senses
from colony.observer import persist as persist_observer
from colony.proposer import propose
from colony.shadow_orchestrator import cycle as shadow_cycle
from colony.spep_worker import process as process_spep
from colony.spep_mark import mark as mark_spep
from colony.queen_scouts import process as process_queen_scouts, advance_lifecycle
from colony.reversal_tournament import process as process_reversal_tournament, maybe_cull as maybe_cull_reversal
from colony.family_tournament import process_all as process_family_tournaments, maybe_cull_all as maybe_cull_family_tournaments
from colony.continuous_evolution import replenish as replenish_evolution, cull_obvious_failures, enforce_elite_training_only, challenger_turnover, challenger_queue_status, promote_reversal_elite_to_production_pool, evolve_reversal_forward
from colony.spartan_alumni import process as process_spartan_alumni, evolve as evolve_spartan_alumni

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
FAST_SECONDS=60
MAINTENANCE_EVERY=5
LIFECYCLE_EVERY=10

async def main():
    await init_db(); cycle=0
    while True:
        cycle+=1
        try:
            result=await process(); logging.info('forward_colony %s',result)
            async with connection() as c:
                rt=await process_reversal_tournament(c)
                ftr=await process_family_tournaments(c)
            logging.info('reversal_tournament %s',rt)
            logging.info('family_tournaments %s',ftr)
            async with connection() as c:
                alumni=await process_spartan_alumni(c)
            logging.info('spartan_alumni %s',alumni)

            spep=await process_spep(result.get('run')) if result.get('run') else {}
            logging.info('spep %s',spep)
            logging.info('spep_marks %s',await mark_spep())
            logging.info('control_colonies %s',await process_controls())
            logging.info('sensory_memory %s',await process_senses())
            logging.info('queen_scouts %s',await process_queen_scouts())

            # Expensive ranking/culling/governance work does not need a 60-second cadence.
            if cycle % MAINTENANCE_EVERY == 1:
                async with connection() as c:
                    elite_policy=await enforce_elite_training_only(c)
                    rtc=await maybe_cull_reversal(c)
                    ftc=await maybe_cull_family_tournaments(c)
                    early=await cull_obvious_failures(c)
                    evolved=await replenish_evolution(c)
                    challengers=await challenger_turnover(c)
                    queue_state=await challenger_queue_status(c)
                    promotions=await promote_reversal_elite_to_production_pool(c,20,5)
                    reversal_evolution=await evolve_reversal_forward(c)
                    alumni_evolution=await evolve_spartan_alumni(c)
                if elite_policy: logging.info('elite_training_policy %s',elite_policy)
                logging.info('reversal_tournament_cull %s',rtc)
                logging.info('family_tournament_culls %s',ftc)
                if early: logging.info('continuous_culls %s',early)
                if evolved: logging.info('continuous_evolution %s',evolved)
                if challengers: logging.info('challenger_turnover %s',challengers)
                logging.info('challenger_queue %s',queue_state)
                if promotions: logging.info('reversal_production_pool %s',promotions)
                logging.info('spartan_alumni_evolution %s',alumni_evolution)
                logging.info('reversal_evolution_v2 %s',reversal_evolution)
                logging.info('observer %s',await persist_observer())
                logging.info('proposal_gate %s',await propose())
                shadow=await shadow_cycle(result.get('run')) if result.get('run') else {}
                logging.info('shadow_ecology %s',shadow)

            if cycle % LIFECYCLE_EVERY == 1:
                logging.info('queen_lifecycle %s',await advance_lifecycle())
        except Exception:
            logging.exception('forward_colony_error')
        await asyncio.sleep(FAST_SECONDS)

if __name__=='__main__': asyncio.run(main())

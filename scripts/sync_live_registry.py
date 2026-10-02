#!/usr/bin/env python3
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db import init_db, connection
from colony.live_registry import ensure_schema, seed_reference_ants, sync_spartan_passers

async def main(path):
    await init_db()
    with open(path) as f: benchmark=json.load(f)
    async with connection() as c:
        await ensure_schema(c)
        ref=await seed_reference_ants(c,benchmark)
        sp=await sync_spartan_passers(c)
        rows=await c.fetch("SELECT family,species,genome_id,promotion_stage,spartan_passed,canary_passed FROM live_ant_registry WHERE live_candidate=true ORDER BY family,species")
    print(json.dumps({'reference':ref,'spartan':sp,'registry':[dict(r) for r in rows]},default=str,indent=2))

if __name__=='__main__':
    asyncio.run(main(sys.argv[1] if len(sys.argv)>1 else 'benchmarks/eve_reference_ants_v2.json'))

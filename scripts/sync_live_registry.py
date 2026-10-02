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
        experiment=str(benchmark.get('experiment') or 'eve_reference')
        safe_summary={k:benchmark.get(k) for k in ('status','experiment','cohort_name','design_rule','proof_rule','freeze_sha256','prospective_after','economics_stress','historical_rows','historical_unique_mints','chronological_folds')}
        exists=await c.fetchval("SELECT 1 FROM historical_nursery_runs WHERE family=$1 AND summary->>'freeze_sha256'=$2 LIMIT 1",experiment,str(benchmark.get('freeze_sha256')))
        if not exists:
            await c.execute("INSERT INTO historical_nursery_runs(family,tested_genomes,historical_rows,finalists,summary) VALUES($1,$2,$3,$4::jsonb,$5::jsonb)",
                            experiment,len(benchmark.get('ants') or []),int(benchmark.get('historical_rows') or 0),json.dumps(benchmark.get('ants') or []),json.dumps(safe_summary))
        sp=await sync_spartan_passers(c)
        rows=await c.fetch("SELECT family,species,genome_id,promotion_stage,spartan_passed,canary_passed FROM live_ant_registry WHERE live_candidate=true ORDER BY family,species")
    print(json.dumps({'reference':ref,'spartan':sp,'registry':[dict(r) for r in rows]},default=str,indent=2))

if __name__=='__main__':
    asyncio.run(main(sys.argv[1] if len(sys.argv)>1 else 'benchmarks/eve_reference_ants_v3.json'))

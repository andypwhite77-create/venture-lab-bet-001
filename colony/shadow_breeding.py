"""Create deterministic counterfactual children for shadow plans only."""
import json,hashlib
from db import connection
from colony.inheritance import offspring
from colony.genome import genome_id

def seed_for(plan_id,parent_id,slot):
    return int(hashlib.sha256(f'{plan_id}:{parent_id}:{slot}'.encode()).hexdigest()[:8],16)

async def breed_plan(plan_id,max_children=10):
    async with connection() as conn:
        p=await conn.fetchrow("SELECT * FROM colony_shadow_plans WHERE id=$1",plan_id)
        if not p:return {'created':0,'reason':'missing_plan'}
        plan=p['plan'] if isinstance(p['plan'],dict) else json.loads(p['plan'])
        breeders=plan.get('breeders',[])[:max_children]
        made=[]
        for slot,parent_id in enumerate(breeders):
            row=await conn.fetchrow("SELECT genome FROM colony_genomes WHERE genome_id=$1",parent_id)
            if not row:continue
            parent=row['genome'] if isinstance(row['genome'],dict) else json.loads(row['genome'])
            child=offspring(parent,seed=seed_for(plan_id,parent_id,slot)); gid=genome_id(child)
            cid=await conn.fetchval("""INSERT INTO colony_shadow_descendants(shadow_plan_id,genome_id,parent_ids,genome)
              VALUES($1,$2,$3::jsonb,$4::jsonb) ON CONFLICT DO NOTHING RETURNING id""",plan_id,gid,json.dumps([parent_id]),json.dumps(child))
            if cid:made.append(gid)
        return {'created':len(made),'genome_ids':made,'breeders_available':len(breeders)}

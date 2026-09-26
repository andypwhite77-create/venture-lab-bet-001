"""Freeze a generation into a prospective run."""
import hashlib, json, subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from forward import population_hash
ROOT=Path(__file__).resolve().parent

def main():
    pop=json.load(open(ROOT/'generation-3.json'))
    ph=population_hash(pop); now=datetime.now(timezone.utc)
    run='fwd-g3-'+now.strftime('%Y%m%dT%H%M%SZ')
    until=now+timedelta(hours=48)
    payload=json.dumps(pop,separators=(',',':')).replace("'","''")
    sql=("INSERT INTO colony_forward_runs(run_id,generation,population_hash,population,frozen_until) "
         f"VALUES ('{run}',3,'{ph}','{payload}'::jsonb,'{until.isoformat()}');")
    subprocess.check_call(['docker','compose','exec','-T','postgres','psql','-U','venturelab','-d','venturelab','-c',sql],cwd=ROOT.parent)
    print(json.dumps({'run_id':run,'generation':3,'ants':len(pop),'population_hash':ph,'frozen_until':until.isoformat()},indent=2))
if __name__=='__main__': main()

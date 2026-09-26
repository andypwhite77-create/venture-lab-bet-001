"""Score a generation on archived 15-minute outcomes, deduplicated by token."""
import json, subprocess, sys
from pathlib import Path
from evaluator import matches
from genome import genome_id
from replay import flatten
from selection import ant_metrics, select, reproduce, classify

ROOT=Path(__file__).resolve().parent
SQL="""COPY (SELECT c.mint,c.features::text,c.market::text,o.net_return_pct FROM research_candidates c JOIN research_outcomes o ON o.candidate_id=c.id WHERE o.horizon_minutes=15 ORDER BY c.created_at) TO STDOUT WITH CSV"""

def load_rows():
    cmd=["docker","compose","exec","-T","postgres","psql","-U","venturelab","-d","venturelab","-c",SQL]
    text=subprocess.check_output(cmd,cwd=ROOT.parent,text=True)
    import csv, io
    rows=[]
    for mint,features,market,ret in csv.reader(io.StringIO(text)):
        rows.append({"mint":mint,"features":json.loads(features),"market":json.loads(market),"ret":float(ret)})
    return rows

def main():
    pop=json.load(open(ROOT/"generation-1.json")); rows=load_rows(); metrics={}
    for g in pop:
        hits=[]
        for row in rows:
            if matches(g,flatten(row)): hits.append((row["mint"],row["ret"]))
        metrics[genome_id(g)]=ant_metrics(hits)
    survivors=select(pop,metrics,20,.40); nextgen=reproduce(survivors,100,260927)
    json.dump(nextgen,open(ROOT/"generation-2.json","w"),indent=2)
    ranked=sorted(pop,key=lambda g:metrics[genome_id(g)]["fitness"],reverse=True)
    report={"observations":len(rows),"generation":len(pop),"survivors":len(survivors),
      "families_surviving":{f:sum(g["family"]==f for g in survivors) for f in sorted({g["family"] for g in survivors})},
      "states":{},"top":[]}
    for g in pop:
        s=classify(metrics[genome_id(g)]); report["states"][s]=report["states"].get(s,0)+1
    for g in ranked[:8]:
        m=metrics[genome_id(g)]; report["top"].append({"family":g["family"],"id":genome_id(g),**m,"parameters":g["parameters"]})
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()

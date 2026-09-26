"""Generation scorer honoring each ant's evolved hold-time gene."""
import csv, io, json, subprocess
from pathlib import Path
from evaluator import matches
from genome import genome_id
from horizons import outcome_for_hold
from replay import flatten
from selection import ant_metrics, select, reproduce, classify
ROOT=Path(__file__).resolve().parent
SQL="""COPY (SELECT c.id,c.mint,c.features::text,c.market::text,o.horizon_minutes,o.net_return_pct FROM research_candidates c JOIN research_outcomes o ON o.candidate_id=c.id ORDER BY c.created_at,o.horizon_minutes) TO STDOUT WITH CSV"""

def load_rows():
    cmd=["docker","compose","exec","-T","postgres","psql","-U","venturelab","-d","venturelab","-c",SQL]
    rows={}
    for r in csv.reader(io.StringIO(subprocess.check_output(cmd,cwd=ROOT.parent,text=True))):
        cid,mint,features,market,h,ret=r
        x=rows.setdefault(cid,{"mint":mint,"features":json.loads(features),"market":json.loads(market),"outcomes":{}})
        x["outcomes"][int(h)]=float(ret)
    return list(rows.values())

def main():
    pop=json.load(open(ROOT/"generation-2.json")); rows=load_rows(); metrics={}; used={}
    for g in pop:
        hits=[]; horizons={}; hold=g.get("parameters",{}).get("hold_minutes",15)
        for row in rows:
            if matches(g,flatten(row)):
                h,ret=outcome_for_hold(row["outcomes"],hold)
                if ret is not None: hits.append((row["mint"],ret)); horizons[h]=horizons.get(h,0)+1
        gid=genome_id(g); metrics[gid]=ant_metrics(hits); used[gid]=horizons
    survivors=select(pop,metrics,20,.40); nextgen=reproduce(survivors,100,260928)
    json.dump(nextgen,open(ROOT/"generation-3.json","w"),indent=2)
    ranked=sorted(pop,key=lambda g:metrics[genome_id(g)]["fitness"],reverse=True)
    report={"candidate_rows":len(rows),"generation":len(pop),"survivors":len(survivors),"states":{},"top":[]}
    for g in pop:
        s=classify(metrics[genome_id(g)]); report["states"][s]=report["states"].get(s,0)+1
    for g in ranked[:10]:
        gid=genome_id(g); m=metrics[gid]
        report["top"].append({"family":g["family"],"id":gid,"hold_requested":g["parameters"].get("hold_minutes"),"horizons_used":used[gid],**m,"parameters":g["parameters"]})
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()

"""Dedicated Reversal evolutionary tournament.

Runs beside the frozen colony without changing its population. Evidence is prospective,
unique-mint scored, and the baseline Reversal is immortal. No live execution authority.
"""
from __future__ import annotations
import copy, json, math, random, statistics
from datetime import datetime, timezone
from pathlib import Path

from colony.forward import eligible
from colony.genome import genome_id
from colony.selection import ant_metrics

ROOT = Path(__file__).resolve().parent
DEFAULT_SEED = 28092026
STAGES = [
    # population, minimum cumulative independent mints before cull, survivors
    (100, 20, 60),
    (60, 35, 30),
    (30, 40, 15),
    (15, 50, 5),
    # finalists are frozen: require 25 NEW independent mints after stage start
    (5, 25, 5),
]
COHORTS = ("drop_threshold", "buy_ratio", "hold", "cooldown", "mixed")


def baseline_genome() -> dict:
    founders = json.load(open(ROOT / "control-founders.json"))
    return copy.deepcopy(next(g for g in founders if g["family"] == "reversal"))


def _bounded(g: dict, key: str, value: float):
    lo, hi = g["bounds"][key]
    old = g["parameters"][key]
    value = max(lo, min(hi, value))
    g["parameters"][key] = int(round(value)) if isinstance(old, int) else round(float(value), 6)


def _variant(parent: dict, cohort: str, rng: random.Random, ordinal: int) -> dict:
    g = copy.deepcopy(parent)
    p = g["parameters"]
    changed = []
    def shift(key, sigma):
        old = p[key]
        scale = max(abs(float(old)), 1.0)
        val = float(old) + rng.gauss(0, sigma * scale)
        _bounded(g, key, val)
        if g["parameters"][key] == old:
            lo, hi = g["bounds"][key]
            step = 1 if isinstance(old, int) else max(abs(float(old))*0.02, 0.002)
            _bounded(g, key, old + (step if rng.random() < .5 else -step))
        changed.append(key)
    if cohort == "drop_threshold": shift("price_change_m5_max", .20)
    elif cohort == "buy_ratio": shift("dex_buy_ratio_m5_min", .10)
    elif cohort == "hold": shift("hold_minutes", .45)
    elif cohort == "cooldown":
        # Founder cooldown is zero, so explore a deliberately broad but bounded window.
        _bounded(g, "cooldown_minutes", rng.choice([0, 3, 5, 8, 10, 15, 20, 30, 45, 60]))
        changed.append("cooldown_minutes")
    else:
        keys = rng.sample(["price_change_m5_max", "dex_buy_ratio_m5_min", "hold_minutes", "cooldown_minutes"], 2)
        for key in keys:
            if key == "price_change_m5_max": shift(key, .16)
            elif key == "dex_buy_ratio_m5_min": shift(key, .08)
            elif key == "hold_minutes": shift(key, .35)
            else:
                _bounded(g, key, rng.choice([0, 3, 5, 8, 10, 15, 20, 30, 45, 60]))
                changed.append(key)
    g["tournament"] = {"cohort": cohort, "ordinal": ordinal, "seed": DEFAULT_SEED, "changed": changed}
    return g


def make_population(size: int = 100, seed: int = DEFAULT_SEED) -> list[dict]:
    if size < 2: raise ValueError("population must include baseline plus variants")
    rng = random.Random(seed); base = baseline_genome(); out = [base]; seen = {genome_id(base)}
    i = 0
    while len(out) < size:
        cohort = COHORTS[i % len(COHORTS)]
        g = _variant(base, cohort, rng, i)
        gid = genome_id(g)
        if gid not in seen:
            out.append(g); seen.add(gid)
        i += 1
        if i > size * 100: raise RuntimeError("could not create unique Reversal population")
    return out


def outlier_dependence(vals: list[float]) -> float:
    pos = [x for x in vals if x > 0]
    if not pos: return 1.0
    total = sum(pos)
    return max(pos) / total if total else 1.0


def score_record(returns: list[tuple[str,float]], baseline_map: dict[str,float]) -> dict:
    first = {}
    for mint, ret in returns: first.setdefault(mint, float(ret))
    vals = list(first.values())
    m = ant_metrics(list(first.items()))
    shared = [(r, baseline_map[mint]) for mint, r in first.items() if mint in baseline_map]
    edge = statistics.fmean(r-b for r,b in shared) if shared else 0.0
    tail = abs(min(0.0, min(vals))) if vals else 100.0
    outlier = outlier_dependence(vals)
    # Fitness is already expectancy/robustness/consistency aware. Add explicit control edge,
    # and punish tails / single-moonshot dependence hard enough to stop lucky idiots breeding.
    tournament_score = float(m.get("fitness", -999.0)) + edge/100.0 - tail/200.0 - max(0.0, outlier-.45)
    return {**m, "baseline_edge_pct": edge, "baseline_overlap_n": len(shared),
            "worst_return_pct": min(vals) if vals else None, "outlier_dependence": outlier,
            "tournament_score": tournament_score, "mints": set(first)}


def rank_with_correlation(records: dict[str,dict]) -> list[tuple[str,dict]]:
    base_ranked = sorted(records.items(), key=lambda kv: kv[1]["tournament_score"], reverse=True)
    selected=[]
    for gid, rec in base_ranked:
        penalty=0.0
        for _, stronger in selected[:20]:
            a,b=rec["mints"],stronger["mints"]
            if a or b:
                j=len(a&b)/max(1,len(a|b))
                if j>.90: penalty=max(penalty,(j-.90)*2.0)
        rec=dict(rec); rec["correlation_penalty"]=penalty; rec["adjusted_score"]=rec["tournament_score"]-penalty
        selected.append((gid,rec))
    return sorted(selected,key=lambda kv:kv[1]["adjusted_score"],reverse=True)


def catastrophic(rec: dict) -> bool:
    # Immediate hard fail for repeated severe tails; one early -25% event is a warning, not auto-death.
    return rec.get("n",0) >= 8 and rec.get("catastrophe_rate",0) >= .20


def eligible_for_reproduction(rec: dict, minimum_n: int) -> bool:
    return rec.get("n",0) >= minimum_n and not catastrophic(rec) and rec.get("baseline_overlap_n",0) >= min(5, minimum_n)


async def process(conn) -> dict:
    run = await conn.fetchrow("SELECT * FROM reversal_tournament_runs WHERE status='collecting' ORDER BY created_at DESC LIMIT 1")
    if not run: return {"run": None, "inserted": 0}
    ants = await conn.fetch("SELECT genome_id,genome FROM reversal_tournament_ants WHERE run_id=$1 AND active=true", run["run_id"])
    rows = await conn.fetch("SELECT id,created_at,mint,features,market FROM research_candidates WHERE created_at >= $1 AND id > $2 ORDER BY id", run["created_at"], run["last_candidate_id"])
    inserted=0
    for row in rows:
        r=dict(row)
        for ant in ants:
            g=ant["genome"]; g=json.loads(g) if isinstance(g,str) else g
            gid=ant["genome_id"]; cooldown=int(g.get("parameters",{}).get("cooldown_minutes",0))
            prev=await conn.fetchval("SELECT max(observed_at) FROM reversal_tournament_entries WHERE run_id=$1 AND genome_id=$2 AND mint=$3",run["run_id"],gid,r["mint"])
            if not eligible(g,r,prev): continue
            hold=int(g.get("parameters",{}).get("hold_minutes",15))
            result=await conn.execute("""INSERT INTO reversal_tournament_entries
              (run_id,genome_id,mint,candidate_id,observed_at,hold_minutes,stage_index)
              VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING""",
              run["run_id"],gid,r["mint"],r["id"],r["created_at"],hold,run["stage_index"])
            inserted += int(result.endswith("1"))
    if rows:
        await conn.execute("UPDATE reversal_tournament_runs SET last_candidate_id=$2 WHERE run_id=$1", run["run_id"], rows[-1]["id"])
    return {"run":run["run_id"],"active_ants":len(ants),"candidates":len(rows),"inserted":inserted}


async def metrics(conn, run_id: str, since=None) -> dict[str,dict]:
    clause=" AND e.observed_at >= $2" if since else ""
    args=[run_id] + ([since] if since else [])
    rows=await conn.fetch(f"""SELECT e.genome_id,e.mint,o.net_return_pct
      FROM reversal_tournament_entries e
      JOIN research_outcomes o ON o.candidate_id=e.candidate_id
      WHERE e.run_id=$1 {clause} AND o.horizon_minutes=(SELECT horizon_minutes FROM research_outcomes
        WHERE candidate_id=e.candidate_id ORDER BY abs(horizon_minutes-e.hold_minutes),horizon_minutes LIMIT 1)
      ORDER BY e.genome_id,e.observed_at""",*args)
    grouped={}
    for r in rows: grouped.setdefault(r["genome_id"],[]).append((r["mint"],float(r["net_return_pct"])))
    baseline_gid=await conn.fetchval("SELECT genome_id FROM reversal_tournament_ants WHERE run_id=$1 AND baseline=true",run_id)
    base_first={}
    for mint,ret in grouped.get(baseline_gid,[]): base_first.setdefault(mint,ret)
    return {gid:score_record(vals,base_first) for gid,vals in grouped.items()}


async def maybe_cull(conn) -> dict:
    run=await conn.fetchrow("SELECT * FROM reversal_tournament_runs WHERE status='collecting' ORDER BY created_at DESC LIMIT 1")
    if not run:return {"run":None}
    idx=int(run["stage_index"]); stage_size,min_n,target=STAGES[min(idx,len(STAGES)-1)]
    active=await conn.fetch("SELECT genome_id,baseline,cohort FROM reversal_tournament_ants WHERE run_id=$1 AND active=true",run["run_id"])
    # Final-five holdout only counts evidence arriving after the finalists were frozen.
    since=run["stage_started_at"] if stage_size==5 else None
    recs=await metrics(conn,run["run_id"],since=since)
    baseline_gid=next((a["genome_id"] for a in active if a["baseline"]),None)
    qualified=[a for a in active if recs.get(a["genome_id"],{}).get("n",0)>=min_n]
    required_qualified = len(active) if stage_size==5 else max(2,math.ceil(len(active)*.80))
    if len(qualified)<required_qualified:
        return {"run":run["run_id"],"stage":stage_size,"active":len(active),"qualified":len(qualified),"minimum_n":min_n,"culled":0}
    if stage_size==5:
        await conn.execute("UPDATE reversal_tournament_runs SET status='holdout_complete' WHERE run_id=$1",run["run_id"])
        return {"run":run["run_id"],"stage":5,"holdout_complete":True,"active":len(active),"minimum_new_n":min_n}

    ranked=rank_with_correlation({a["genome_id"]:recs[a["genome_id"]] for a in active if a["genome_id"] in recs})
    keep=[]
    # Baseline is immortal and never consumes the evidence standard.
    if baseline_gid: keep.append(baseline_gid)
    # Preserve cohort diversity while selecting strong ants. First pass one per cohort.
    cohorts={}
    for a in active: cohorts[a["genome_id"]]=a["cohort"]
    represented=set()
    for gid,rec in ranked:
        if gid==baseline_gid or catastrophic(rec) or not eligible_for_reproduction(rec,min_n): continue
        cohort=cohorts.get(gid,"mixed")
        if cohort not in represented and len(keep)<target:
            keep.append(gid);represented.add(cohort)
    for gid,rec in ranked:
        if len(keep)>=target:break
        if gid in keep or catastrophic(rec) or not eligible_for_reproduction(rec,min_n):continue
        keep.append(gid)
    keep=keep[:target]
    losers=[a["genome_id"] for a in active if a["genome_id"] not in set(keep)]
    if losers:
        await conn.execute("""UPDATE reversal_tournament_ants SET active=false,eliminated_at=now(),eliminated_stage=$3,
          elimination_reason='stage_cull' WHERE run_id=$1 AND genome_id=ANY($2::text[])""",run["run_id"],losers,idx)
    await conn.execute("UPDATE reversal_tournament_runs SET stage_size=$2,stage_index=stage_index+1,stage_started_at=now() WHERE run_id=$1",run["run_id"],target)
    return {"run":run["run_id"],"from":stage_size,"to":target,"culled":len(losers),"survivors":keep}

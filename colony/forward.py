"""Frozen forward runner. Population cannot mutate during a run."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from colony.evaluator import matches
from colony.genome import genome_id
from colony.replay import flatten

def population_hash(pop):
    blob=json.dumps(pop,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(blob).hexdigest()

def eligible(genome, row, previous_entry_at=None):
    if not matches(genome, flatten(row)): return False
    cooldown=int(genome.get("parameters",{}).get("cooldown_minutes",0))
    if previous_entry_at is None or cooldown <= 0: return True
    observed=row["created_at"]
    if isinstance(observed,str): observed=datetime.fromisoformat(observed.replace("Z","+00:00"))
    if isinstance(previous_entry_at,str): previous_entry_at=datetime.fromisoformat(previous_entry_at.replace("Z","+00:00"))
    return (observed-previous_entry_at).total_seconds() >= cooldown*60

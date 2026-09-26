"""Shared Prospective Event Panel v1: genome-blind, immutable decision laboratory."""
from __future__ import annotations
import hashlib,json,random
from colony.evaluator import matches
from colony.genome import genome_id
from colony.replay import flatten
VERSION='spep-event-v1'

def event_id(row):
    raw=f"{VERSION}|{row['id']}|{row['created_at']}|{row['mint']}"
    return 'spep_'+hashlib.sha256(raw.encode()).hexdigest()[:20]

def decision(genome,row):
    return 'buy' if matches(genome,flatten(row)) else 'abstain'

def twins(action,event,genome):
    if action=='abstain': return {'original':'abstain','mirror':'abstain','random_direction':'abstain'}
    seed=int(hashlib.sha256(f"{event}|{genome}|random-direction-v1".encode()).hexdigest()[:16],16)
    return {'original':action,'mirror':'sell' if action=='buy' else 'buy','random_direction':random.Random(seed).choice(('buy','sell'))}

def panel_manifest(population):
    return {'event_generator':VERSION,'genomes':len(population),'population_hash':hashlib.sha256(json.dumps(population,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'counterfactuals':'spep-dm-v1'}

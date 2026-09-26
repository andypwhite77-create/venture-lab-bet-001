CREATE TABLE IF NOT EXISTS colony_forward_runs (
 run_id TEXT PRIMARY KEY, generation INT NOT NULL, population_hash TEXT NOT NULL,
 population JSONB NOT NULL, started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 frozen_until TIMESTAMPTZ NOT NULL, status TEXT NOT NULL DEFAULT 'collecting'
);
CREATE TABLE IF NOT EXISTS colony_forward_entries (
 id BIGSERIAL PRIMARY KEY, run_id TEXT NOT NULL REFERENCES colony_forward_runs(run_id),
 genome_id TEXT NOT NULL, family TEXT NOT NULL, mint TEXT NOT NULL,
 candidate_id BIGINT NOT NULL, observed_at TIMESTAMPTZ NOT NULL,
 hold_minutes INT NOT NULL, cooldown_minutes INT NOT NULL,
 UNIQUE(run_id, genome_id, candidate_id)
);
CREATE INDEX IF NOT EXISTS colony_forward_entries_lookup
 ON colony_forward_entries(run_id, genome_id, mint, observed_at DESC);

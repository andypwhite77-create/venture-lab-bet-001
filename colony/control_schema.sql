CREATE TABLE IF NOT EXISTS colony_control_runs (
 control_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
 population_hash TEXT NOT NULL, population JSONB NOT NULL,
 started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 frozen_until TIMESTAMPTZ NOT NULL, status TEXT NOT NULL DEFAULT 'collecting'
);
CREATE TABLE IF NOT EXISTS colony_control_entries (
 id BIGSERIAL PRIMARY KEY, control_id TEXT NOT NULL REFERENCES colony_control_runs(control_id),
 genome_id TEXT NOT NULL, family TEXT NOT NULL, mint TEXT NOT NULL,
 candidate_id BIGINT NOT NULL, observed_at TIMESTAMPTZ NOT NULL,
 hold_minutes INT NOT NULL, cooldown_minutes INT NOT NULL,
 UNIQUE(control_id,genome_id,candidate_id)
);
CREATE INDEX IF NOT EXISTS colony_control_entries_lookup
 ON colony_control_entries(control_id,genome_id,mint,observed_at DESC);

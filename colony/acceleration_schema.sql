CREATE TABLE IF NOT EXISTS historical_nursery_runs (
 id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), family TEXT NOT NULL,
 tested_genomes INT NOT NULL, historical_rows INT NOT NULL, finalists JSONB NOT NULL, summary JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS discovered_patterns (
 id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 rule JSONB NOT NULL, robust_score DOUBLE PRECISION NOT NULL, evidence JSONB NOT NULL,
 status TEXT NOT NULL DEFAULT 'discovery_only'
);
CREATE TABLE IF NOT EXISTS evolution_candidate_queue (
 id BIGSERIAL PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), family TEXT NOT NULL,
 genome_id TEXT NOT NULL, genome JSONB NOT NULL, historical_score DOUBLE PRECISION NOT NULL,
 source_run_id TEXT, provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
 status TEXT NOT NULL DEFAULT 'ready', deployed_at TIMESTAMPTZ, deployed_run_id TEXT,
 UNIQUE(family,genome_id)
);
CREATE INDEX IF NOT EXISTS evolution_candidate_queue_ready ON evolution_candidate_queue(family,status,historical_score DESC);
CREATE TABLE IF NOT EXISTS acceleration_state (
 key TEXT PRIMARY KEY, value JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

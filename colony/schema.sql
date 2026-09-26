CREATE TABLE IF NOT EXISTS colony_genomes (
 id BIGSERIAL PRIMARY KEY, genome_id TEXT UNIQUE NOT NULL, parent_ids TEXT[] NOT NULL DEFAULT '{}', generation INT NOT NULL DEFAULT 0,
 family TEXT NOT NULL, genome JSONB NOT NULL, status TEXT NOT NULL DEFAULT 'scout', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), retired_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS colony_experiments (
 id BIGSERIAL PRIMARY KEY, experiment_id TEXT UNIQUE NOT NULL, genome_id TEXT NOT NULL REFERENCES colony_genomes(genome_id), hypothesis TEXT,
 started_at TIMESTAMPTZ NOT NULL DEFAULT now(), ended_at TIMESTAMPTZ, metrics JSONB NOT NULL DEFAULT '{}', fitness DOUBLE PRECISION, status TEXT NOT NULL DEFAULT 'queued'
);
CREATE TABLE IF NOT EXISTS colony_reviews (
 id BIGSERIAL PRIMARY KEY, experiment_id TEXT REFERENCES colony_experiments(experiment_id), reviewer TEXT NOT NULL,
 verdict TEXT NOT NULL, objections JSONB NOT NULL DEFAULT '[]', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS colony_events (
 id BIGSERIAL PRIMARY KEY, event_type TEXT NOT NULL, payload JSONB NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS colony_state (
 key TEXT PRIMARY KEY, value JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS colony_genomes_family_status_idx ON colony_genomes(family,status);
CREATE INDEX IF NOT EXISTS colony_experiments_genome_idx ON colony_experiments(genome_id,started_at DESC);

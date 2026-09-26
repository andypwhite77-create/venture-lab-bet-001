CREATE TABLE IF NOT EXISTS colony_sensory_snapshots (
 id BIGSERIAL PRIMARY KEY,
 candidate_id BIGINT,
 mint TEXT NOT NULL,
 observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 source_count INT NOT NULL DEFAULT 0,
 disagreement_ratio DOUBLE PRECISION,
 snapshot JSONB NOT NULL,
 UNIQUE(candidate_id)
);
CREATE INDEX IF NOT EXISTS colony_sensory_mint_time
 ON colony_sensory_snapshots(mint,observed_at DESC);
CREATE TABLE IF NOT EXISTS colony_provider_health (
 id BIGSERIAL PRIMARY KEY,
 provider TEXT NOT NULL,
 observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 ok BOOLEAN NOT NULL,
 latency_ms INT,
 error TEXT
);
CREATE INDEX IF NOT EXISTS colony_provider_health_time
 ON colony_provider_health(provider,observed_at DESC);

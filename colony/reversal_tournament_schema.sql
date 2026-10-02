CREATE TABLE IF NOT EXISTS reversal_tournament_runs (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'collecting',
  stage_size INT NOT NULL DEFAULT 100,
  stage_index INT NOT NULL DEFAULT 0,
  stage_started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_candidate_id BIGINT NOT NULL DEFAULT 0,
  config JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS reversal_tournament_ants (
  run_id TEXT NOT NULL REFERENCES reversal_tournament_runs(run_id) ON DELETE CASCADE,
  genome_id TEXT NOT NULL,
  genome JSONB NOT NULL,
  cohort TEXT NOT NULL,
  baseline BOOLEAN NOT NULL DEFAULT FALSE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  eliminated_at TIMESTAMPTZ,
  eliminated_stage INT,
  elimination_reason TEXT,
  generation INT NOT NULL DEFAULT 0,
  parent_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  born_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(run_id, genome_id)
);
CREATE TABLE IF NOT EXISTS reversal_tournament_entries (
  id BIGSERIAL PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES reversal_tournament_runs(run_id) ON DELETE CASCADE,
  genome_id TEXT NOT NULL,
  mint TEXT NOT NULL,
  candidate_id BIGINT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  hold_minutes INT NOT NULL,
  stage_index INT NOT NULL,
  UNIQUE(run_id, genome_id, candidate_id)
);
CREATE INDEX IF NOT EXISTS reversal_tournament_entries_lookup
  ON reversal_tournament_entries(run_id, genome_id, mint, observed_at DESC);

CREATE TABLE IF NOT EXISTS reversal_evolution_log (
  id BIGSERIAL PRIMARY KEY,
  run_id TEXT NOT NULL,
  generation INT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  active_ants INT NOT NULL,
  born INT NOT NULL DEFAULT 0,
  culled INT NOT NULL DEFAULT 0,
  parent_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  metrics JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS reversal_evolution_log_run_generation
  ON reversal_evolution_log(run_id,generation,observed_at);

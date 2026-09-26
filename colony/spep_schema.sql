CREATE TABLE IF NOT EXISTS colony_spep_events (
 event_id TEXT PRIMARY KEY, generator_version TEXT NOT NULL, candidate_id BIGINT NOT NULL UNIQUE,
 observed_at TIMESTAMPTZ NOT NULL, mint TEXT NOT NULL, observation JSONB NOT NULL,
 observation_hash TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS colony_spep_decisions (
 event_id TEXT NOT NULL REFERENCES colony_spep_events(event_id), genome_id TEXT NOT NULL,
 population TEXT NOT NULL DEFAULT 'gen3-parent', family TEXT NOT NULL,
 original_action TEXT NOT NULL, mirror_action TEXT NOT NULL, random_action TEXT NOT NULL, participation_action TEXT NOT NULL,
 marginal_state TEXT NOT NULL DEFAULT 'flat-reset', path_state JSONB,
 decided_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(event_id,genome_id,population));
CREATE TABLE IF NOT EXISTS colony_spep_marks (
 event_id TEXT NOT NULL, genome_id TEXT NOT NULL, population TEXT NOT NULL,
 policy_variant TEXT NOT NULL, horizon_minutes INT NOT NULL,
 gross_return_pct DOUBLE PRECISION, friction_pct DOUBLE PRECISION, net_return_pct DOUBLE PRECISION,
 measured_at TIMESTAMPTZ NOT NULL, PRIMARY KEY(event_id,genome_id,population,policy_variant,horizon_minutes));

CREATE TABLE IF NOT EXISTS colony_spep_manifests (
 manifest_id TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 t0 TIMESTAMPTZ NOT NULL, run_id TEXT NOT NULL, git_commit TEXT NOT NULL,
 event_generator TEXT NOT NULL, counterfactual_version TEXT NOT NULL,
 population_hash TEXT NOT NULL, manifest JSONB NOT NULL, manifest_hash TEXT NOT NULL UNIQUE);

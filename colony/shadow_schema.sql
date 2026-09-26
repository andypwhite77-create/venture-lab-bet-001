CREATE TABLE IF NOT EXISTS colony_shadow_plans (
 id BIGSERIAL PRIMARY KEY,
 run_id TEXT NOT NULL,
 observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 evidence_cutoff BIGINT,
 plan JSONB NOT NULL,
 UNIQUE(run_id,evidence_cutoff)
);
CREATE INDEX IF NOT EXISTS colony_shadow_plans_time
 ON colony_shadow_plans(run_id,observed_at DESC);

CREATE TABLE IF NOT EXISTS colony_shadow_descendants (
 id BIGSERIAL PRIMARY KEY,
 shadow_plan_id BIGINT NOT NULL REFERENCES colony_shadow_plans(id),
 genome_id TEXT NOT NULL,
 parent_ids JSONB NOT NULL,
 genome JSONB NOT NULL,
 state TEXT NOT NULL DEFAULT 'counterfactual',
 UNIQUE(shadow_plan_id,genome_id)
);

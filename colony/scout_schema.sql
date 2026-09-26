CREATE TABLE IF NOT EXISTS colony_scout_experiments (
 id BIGSERIAL PRIMARY KEY,
 proposal_id BIGINT NOT NULL REFERENCES colony_proposals(id),
 run_id TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 state TEXT NOT NULL DEFAULT 'paper_pending',
 genome_ids JSONB NOT NULL,
 evidence JSONB NOT NULL,
 CHECK(state IN ('paper_pending','paper_running','paper_complete','rejected'))
);
CREATE UNIQUE INDEX IF NOT EXISTS colony_scout_one_per_proposal
 ON colony_scout_experiments(proposal_id);

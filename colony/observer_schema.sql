CREATE TABLE IF NOT EXISTS colony_observer_reports (
 id BIGSERIAL PRIMARY KEY,
 observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 run_id TEXT NOT NULL,
 role TEXT NOT NULL,
 report JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS colony_observer_reports_time
 ON colony_observer_reports(run_id,role,observed_at DESC);

CREATE TABLE IF NOT EXISTS colony_proposals (
 id BIGSERIAL PRIMARY KEY,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 run_id TEXT NOT NULL,
 proposer TEXT NOT NULL,
 proposal_type TEXT NOT NULL,
 proposal JSONB NOT NULL,
 status TEXT NOT NULL DEFAULT 'observer_only',
 CHECK(status IN ('observer_only','rejected','eligible_after_freeze','approved'))
);

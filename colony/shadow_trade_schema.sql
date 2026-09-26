CREATE TABLE IF NOT EXISTS colony_shadow_entries (
 id BIGSERIAL PRIMARY KEY,
 shadow_descendant_id BIGINT NOT NULL REFERENCES colony_shadow_descendants(id),
 mint TEXT NOT NULL,
 candidate_id BIGINT NOT NULL,
 observed_at TIMESTAMPTZ NOT NULL,
 hold_minutes INTEGER NOT NULL,
 UNIQUE(shadow_descendant_id,candidate_id)
);
CREATE INDEX IF NOT EXISTS colony_shadow_entries_candidate
 ON colony_shadow_entries(candidate_id);

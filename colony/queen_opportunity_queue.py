"""Human-reviewed strategic opportunity queue, with no execution path.

Approval means permission to research the thesis, NOT trade, borrow,
manipulate a market, allocate capital, or provision infrastructure.
"""
import json
KINDS=frozenset(('major_asset_short','market_dislocation','cross_venue_arbitrage','colony_expansion','research_infrastructure','other'))
STATUSES=frozenset(('proposed','research_approved','rejected','expired'))
SCHEMA="""CREATE TABLE IF NOT EXISTS queen_opportunity_proposals (
 id BIGSERIAL PRIMARY KEY,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 submitted_by TEXT NOT NULL,
 kind TEXT NOT NULL,
 title TEXT NOT NULL,
 thesis TEXT NOT NULL,
 evidence JSONB NOT NULL DEFAULT '{}',
 failure_modes JSONB NOT NULL DEFAULT '[]',
 requested_resources JSONB NOT NULL DEFAULT '{}',
 risk_notes TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'proposed',
 reviewed_by TEXT,
 reviewed_at TIMESTAMPTZ,
 review_note TEXT,
 CHECK (status IN ('proposed','research_approved','rejected','expired'))
);
CREATE INDEX IF NOT EXISTS queen_opportunity_proposals_status_time
 ON queen_opportunity_proposals(status,created_at DESC);
"""
def validate_submission(kind,title,thesis,source,evidence,risks):
 if kind not in KINDS:raise ValueError('invalid_kind')
 if not source or len(source)>80:raise ValueError('invalid_source')
 if not 8<=len(title)<=160:raise ValueError('invalid_title')
 if not 20<=len(thesis)<=4000:raise ValueError('invalid_thesis')
 if not isinstance(evidence,dict) or not evidence:raise ValueError('evidence_required')
 if not isinstance(risks,list) or not risks:raise ValueError('failure_modes_required')
async def ensure_schema(conn):
 await conn.execute(SCHEMA)
async def submit(conn,kind,title,thesis,source,evidence,risks,resources=None,notes=''):
 validate_submission(kind,title,thesis,source,evidence,risks)
 await ensure_schema(conn)
 return await conn.fetchval("""INSERT INTO queen_opportunity_proposals
 (submitted_by,kind,title,thesis,evidence,failure_modes,requested_resources,risk_notes)
 VALUES($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7::jsonb,$8) RETURNING id""",
 source,kind,title,thesis,json.dumps(evidence),json.dumps(risks),json.dumps(resources or {}),notes)
async def review(conn,proposal_id,decision,reviewer,note):
 if decision not in ('research_approved','rejected'):raise ValueError('invalid_review_decision')
 if not note or len(note)>2000:raise ValueError('review_reason_required')
 await ensure_schema(conn)
 return await conn.fetchrow("""UPDATE queen_opportunity_proposals
 SET status=$2,reviewed_by=$3,review_note=$4,reviewed_at=now(),updated_at=now()
 WHERE id=$1 AND status='proposed'
 RETURNING id,status,reviewed_at""",proposal_id,decision,reviewer,note)

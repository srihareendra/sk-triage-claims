-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_diskann CASCADE;

-- ===============================
-- Customers
-- ===============================
DROP TABLE IF EXISTS claim_notes CASCADE;
DROP TABLE IF EXISTS triage_decisions CASCADE;
DROP TABLE IF EXISTS claims CASCADE;
DROP TABLE IF EXISTS policies CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
  customer_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  state CHAR(2),
  age INT
);

-- ===============================
-- Policies
-- ===============================
CREATE TABLE policies (
  policy_id SERIAL PRIMARY KEY,
  customer_id INT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
  policy_type TEXT CHECK (policy_type IN ('AUTO','HOME','HEALTH')),
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  premium NUMERIC(12,2) NOT NULL
);

-- ===============================
-- Claims
-- ===============================
CREATE TABLE claims (
  claim_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  policy_id INT NOT NULL REFERENCES policies(policy_id) ON DELETE CASCADE,
  date_of_loss DATE NOT NULL,
  description TEXT,
  amount_claimed NUMERIC(12,2),
  status TEXT DEFAULT 'OPEN'
);
-- ===============================
-- Triage Decisions
-- ===============================
CREATE TABLE triage_decisions (
  decision_id SERIAL PRIMARY KEY,
  claim_id INT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
  severity TEXT CHECK (severity IN ('LOW','MEDIUM','HIGH')),
  fraud_risk NUMERIC(4,3) CHECK (fraud_risk >= 0 AND fraud_risk <= 1),
  route_to TEXT CHECK (route_to IN ('OPERATIONS','SIU')),
  rationale TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ===============================
-- Claim Notes
-- ===============================
CREATE TABLE claim_notes (
  note_id SERIAL PRIMARY KEY,
  claim_id INT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
  note_text TEXT,
  embedding vector(1536)
);

-- Vector Index for ANN
CREATE INDEX IF NOT EXISTS idx_claim_notes_embedding
  ON claim_notes
  USING diskann (embedding vector_cosine_ops);

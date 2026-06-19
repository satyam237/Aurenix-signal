-- AureniX Signal v1.0 initial schema (Phase 0-1)

CREATE TABLE IF NOT EXISTS prompts (
  id TEXT PRIMARY KEY,
  brand_id TEXT NOT NULL,
  text TEXT NOT NULL,
  category TEXT NOT NULL,
  intent_tag TEXT,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS run_batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  total_prompts INT DEFAULT 0,
  success_count INT DEFAULT 0,
  failure_count INT DEFAULT 0,
  skipped_count INT DEFAULT 0,
  total_cost_usd NUMERIC(10, 6) DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'running',
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS raw_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id TEXT REFERENCES prompts(id),
  engine TEXT NOT NULL,
  model TEXT NOT NULL,
  response_text TEXT NOT NULL DEFAULT '',
  response_json JSONB,
  tokens_in INT,
  tokens_out INT,
  cost_usd NUMERIC(10, 6),
  status TEXT NOT NULL,
  error_message TEXT,
  run_batch_id UUID REFERENCES run_batches(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS brand_config (
  brand_id TEXT PRIMARY KEY,
  truth_registry JSONB NOT NULL,
  settings JSONB DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_run_id UUID REFERENCES raw_runs(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_runs_prompt_engine_created
  ON raw_runs (prompt_id, engine, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_runs_batch
  ON raw_runs (run_batch_id);

CREATE INDEX IF NOT EXISTS idx_raw_runs_status_created
  ON raw_runs (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_run_batches_started
  ON run_batches (started_at DESC);

ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE run_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;

-- MVP: service role bypasses RLS; anon/authenticated blocked until v2.0 policies

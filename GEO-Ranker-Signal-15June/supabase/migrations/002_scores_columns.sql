-- Phase 2: Response Judge + GEO Score columns on scores table

ALTER TABLE scores
  ADD COLUMN IF NOT EXISTS brand_mentioned BOOLEAN,
  ADD COLUMN IF NOT EXISTS mention_position NUMERIC(5, 4),
  ADD COLUMN IF NOT EXISTS sentiment NUMERIC(5, 4),
  ADD COLUMN IF NOT EXISTS factual_accuracy NUMERIC(5, 4),
  ADD COLUMN IF NOT EXISTS geo_score NUMERIC(5, 4),
  ADD COLUMN IF NOT EXISTS judge_model TEXT,
  ADD COLUMN IF NOT EXISTS details JSONB DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS idx_scores_raw_run_id
  ON scores (raw_run_id);

CREATE INDEX IF NOT EXISTS idx_scores_geo_score
  ON scores (geo_score DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_scores_created
  ON scores (created_at DESC);

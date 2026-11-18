-- Phase 2 (PDF-aligned): discrete scorer columns on scores

ALTER TABLE scores
  ADD COLUMN IF NOT EXISTS inclusion_score INT,
  ADD COLUMN IF NOT EXISTS rank_score INT,
  ADD COLUMN IF NOT EXISTS accuracy_score INT,
  ADD COLUMN IF NOT EXISTS citation_score INT,
  ADD COLUMN IF NOT EXISTS sentiment_score INT;

CREATE INDEX IF NOT EXISTS idx_scores_inclusion
  ON scores (inclusion_score DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_scores_rank
  ON scores (rank_score DESC NULLS LAST);

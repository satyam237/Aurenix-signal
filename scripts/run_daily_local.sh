#!/usr/bin/env bash
# Local daily run (no GCP): prompt pipeline + optional GEO score backfill.
# Usage:
#   ./scripts/run_daily_local.sh              # cron --force + score unscored runs (heuristic)
#   ./scripts/run_daily_local.sh --llm        # same, but LLM judge for accuracy/sentiment
#   ./scripts/run_daily_local.sh --score-only # skip pipeline; only backfill scores
#   ./scripts/run_daily_local.sh --no-score   # pipeline only
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

DO_PIPELINE=1
DO_SCORE=1
SKIP_LLM=1
LIMIT="${SCORE_LIMIT:-100}"

for arg in "$@"; do
  case "$arg" in
    --score-only) DO_PIPELINE=0 ;;
    --no-score) DO_SCORE=0 ;;
    --llm) SKIP_LLM=0 ;;
    --help|-h)
      sed -n '2,8p' "$0"
      exit 0
      ;;
  esac
done

if [[ "$DO_PIPELINE" -eq 1 ]]; then
  echo "=== Local cron: prompt runner (--force) ==="
  "$PYTHON" -m backend.scheduler.cron_runner --force
fi

if [[ "$DO_SCORE" -eq 1 ]]; then
  echo "=== Score unscored raw_runs (limit=$LIMIT, skip_llm=$SKIP_LLM) ==="
  SCORE_ARGS=(--supabase --limit "$LIMIT")
  if [[ "$SKIP_LLM" -eq 1 ]]; then
    SCORE_ARGS+=(--skip-llm)
  fi
  "$PYTHON" scripts/backfill_scores.py "${SCORE_ARGS[@]}"
fi

echo "Done. Health: streamlit run dashboard/health_app.py"

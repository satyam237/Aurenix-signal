#!/usr/bin/env bash
# End-to-end Supabase setup: verify schema → seed → smoke pipeline → verify.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

echo "=== Step 1: Verify schema ==="
"$PYTHON" scripts/apply_schema.py --check-only

echo ""
echo "=== Step 2: Seed prompts + brand config ==="
"$PYTHON" scripts/seed_supabase.py

echo ""
echo "=== Step 3: Readiness check ==="
"$PYTHON" scripts/check_ready.py

echo ""
echo "=== Step 4: Pipeline smoke test (2 prompts) ==="
"$PYTHON" -m backend.agents.prompt_runner.pipeline --limit 2

echo ""
echo "=== Step 5: Phase 1 verification ==="
"$PYTHON" scripts/verify_phase1.py

echo ""
echo "Setup complete. Check Supabase tables: run_batches, raw_runs."

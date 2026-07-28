#!/usr/bin/env bash
# End-to-end Supabase setup: verify schema → seed → smoke pipeline → verify.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Step 1: Verify schema ==="
python3 scripts/apply_schema.py --check-only

echo ""
echo "=== Step 2: Seed prompts + brand config ==="
python3 scripts/seed_supabase.py

echo ""
echo "=== Step 3: Readiness check ==="
python3 scripts/check_ready.py

echo ""
echo "=== Step 4: Pipeline smoke test (2 prompts) ==="
python3 -m backend.agents.prompt_runner.pipeline --limit 2

echo ""
echo "=== Step 5: Phase 1 verification ==="
python3 scripts/verify_phase1.py

echo ""
echo "Setup complete. Check Supabase tables: run_batches, raw_runs."

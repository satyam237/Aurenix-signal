#!/usr/bin/env python3
"""Verify Phase 0-1 implementation checklist."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_PATHS = [
    "README.md",
    "pyproject.toml",
    "data/prompts/nautikal_prompts.json",
    "data/brands/nautikal_truth_registry.json",
    "data/baseline/week0_baseline.csv",
    "supabase/migrations/001_initial_schema.sql",
    "backend/agents/prompt_runner/pipeline.py",
    "backend/agents/prompt_runner/adapters/openai_adapter.py",
    "backend/agents/prompt_runner/adapters/gemini_adapter.py",
    "backend/scheduler/cron_runner.py",
    "dashboard/health_app.py",
    "scripts/seed_supabase.py",
    "scripts/apply_schema.py",
    "scripts/setup_supabase.sh",
    "scripts/test_api_keys.py",
    "scripts/check_ready.py",
    "scripts/bulk_prompt_test.py",
]


def check_files() -> list[str]:
    missing = [p for p in REQUIRED_PATHS if not (ROOT / p).exists()]
    return missing


def check_prompts() -> list[str]:
    errors: list[str] = []
    path = ROOT / "data" / "prompts" / "nautikal_prompts.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if len(data.get("prompts", [])) != 25:
        errors.append(f"Expected 25 prompts, found {len(data.get('prompts', []))}")
    return errors


def check_supabase_connection() -> tuple[bool, str]:
    from backend.shared.config import get_settings
    from backend.shared.supabase_client import get_supabase_client

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return False, "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in .env"

    required_tables = ("prompts", "run_batches", "raw_runs", "brand_config", "scores")
    try:
        client = get_supabase_client(settings)
        missing: list[str] = []
        counts: list[str] = []
        for table in required_tables:
            try:
                result = client.table(table).select("id", count="exact").limit(1).execute()
                count = result.count if result.count is not None else len(result.data)
                counts.append(f"{table}={count}")
            except Exception as exc:
                if "PGRST205" in str(exc) or "Could not find the table" in str(exc):
                    missing.append(table)
                else:
                    raise
        if missing:
            return False, f"Schema incomplete — missing tables: {', '.join(missing)}"
        return True, f"Connected — tables OK ({', '.join(counts)})"
    except Exception as exc:
        return False, f"Supabase connection failed: {exc}"


def main() -> int:
    print("=== AureniX Signal Phase 0-1 Verification ===\n")
    ok = True

    missing = check_files()
    if missing:
        ok = False
        print("FAIL — missing files:")
        for p in missing:
            print(f"  - {p}")
    else:
        print("OK — all required files present")

    prompt_errors = check_prompts()
    if prompt_errors:
        ok = False
        for err in prompt_errors:
            print(f"FAIL — {err}")
    else:
        print("OK — 25 prompts in library")

    baseline = ROOT / "data" / "baseline" / "week0_baseline.csv"
    lines = baseline.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) < 51:
        print(f"WARN — baseline CSV has {len(lines) - 1} rows (expected 50)")
    else:
        print("OK — baseline CSV template has 50 rows")

    connected, msg = check_supabase_connection()
    if connected:
        print(f"OK — {msg}")
    else:
        print(f"WARN — {msg}")
        print("      Run: python scripts/apply_schema.py --print-sql")
        print("      Then: python scripts/seed_supabase.py")

    print("\nRun readiness check: python scripts/check_ready.py")
    print("Run unit tests: pytest -q")
    print("Run API smoke test: python scripts/test_api_keys.py")
    print("Bulk test (local): python scripts/bulk_prompt_test.py --limit 3")
    print("Run pipeline: python -m backend.agents.prompt_runner.pipeline --limit 3")
    print("Run health dashboard: streamlit run dashboard/health_app.py")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

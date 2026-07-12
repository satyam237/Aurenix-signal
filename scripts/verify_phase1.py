#!/usr/bin/env python3
"""Verify Phase 0-1 implementation checklist."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATHS = [
    "README.md",
    "pyproject.toml",
    "data/prompts/nautikal_prompts.json",
    "data/brands/nautikal_truth_registry.json",
    "data/baseline/week0_baseline.csv",
    "supabase/migrations/001_initial_schema.sql",
    "agents/prompt_runner/pipeline.py",
    "agents/prompt_runner/adapters/openai_adapter.py",
    "agents/prompt_runner/adapters/gemini_adapter.py",
    "scheduler/cron_runner.py",
    "dashboard/health_app.py",
    "scripts/seed_supabase.py",
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
    from shared.config import get_settings
    from shared.supabase_client import get_supabase_client

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return False, "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in .env"

    try:
        client = get_supabase_client(settings)
        result = client.table("prompts").select("id", count="exact").limit(1).execute()
        count = result.count if result.count is not None else len(result.data)
        return True, f"Connected — prompts table accessible (sample count={count})"
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
        print(
            "      Apply supabase/migrations/001_initial_schema.sql then run scripts/seed_supabase.py"
        )

    print("\nRun readiness check: python scripts/check_ready.py")
    print("Run unit tests: pytest -q")
    print("Run API smoke test: python scripts/test_api_keys.py")
    print("Bulk test (local): python scripts/bulk_prompt_test.py --limit 3")
    print("Run pipeline: python -m agents.prompt_runner.pipeline --limit 3")
    print("Run health dashboard: streamlit run dashboard/health_app.py")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

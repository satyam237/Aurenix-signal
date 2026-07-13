#!/usr/bin/env python3
"""Check environment readiness before running prompt tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def main() -> int:
    print("=== AureniX Signal — readiness check ===\n")

    if not ENV_PATH.exists():
        print("ACTION REQUIRED: Create your .env file")
        print(f"  cp {ENV_EXAMPLE.name} .env")
        print("  Then edit .env and paste your API keys.\n")
        return 1

    from shared.config import get_settings

    settings = get_settings()
    ready_for_api = True
    ready_for_pipeline = True

    print("API keys:")
    if settings.openai_api_key:
        print(f"  OPENAI_API_KEY     set ({_mask(settings.openai_api_key)})")
    else:
        print("  OPENAI_API_KEY     MISSING — add to .env")
        ready_for_api = False

    if settings.gemini_api_key:
        print(f"  GEMINI_API_KEY     set ({_mask(settings.gemini_api_key)})")
    else:
        print("  GEMINI_API_KEY     MISSING — add to .env")
        ready_for_api = False

    print("\nModels:")
    print(f"  OPENAI_MODEL       {settings.openai_model}")
    print(f"  GEMINI_MODEL       {settings.gemini_model}")

    print("\nSupabase (required for pipeline + dashboard):")
    if settings.supabase_url and settings.supabase_service_role_key:
        print(f"  SUPABASE_URL       set ({settings.supabase_url})")
        print(f"  SERVICE_ROLE_KEY   set ({_mask(settings.supabase_service_role_key)})")
    else:
        print("  SUPABASE_*         not set — bulk local tests still work")
        ready_for_pipeline = False

    print("\nLimits:")
    print(f"  DAILY_COST_CAP_USD ${settings.daily_cost_cap_usd:.2f}")
    print(f"  DEDUP_HOURS        {settings.dedup_hours}h")
    print(f"  BRAND_ID           {settings.brand_id}")

    print()
    if not ready_for_api:
        print("Next steps:")
        print("  1. Edit .env and add OPENAI_API_KEY and/or GEMINI_API_KEY")
        print("  2. Re-run: python scripts/check_ready.py")
        print("  3. Smoke test: python scripts/test_api_keys.py")
        print("  4. Bulk test:  python scripts/bulk_prompt_test.py --limit 3")
        return 1

    print("Ready for API testing.")
    print("\nSuggested commands:")
    print("  python scripts/test_api_keys.py")
    print("  python scripts/bulk_prompt_test.py --limit 3")
    print("  python scripts/bulk_prompt_test.py")

    if not ready_for_pipeline:
        print("\nFor Supabase pipeline runs, also set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY,")
        print("apply supabase/migrations/001_initial_schema.sql, then:")
        print("  python scripts/seed_supabase.py")
        print("  python -m agents.prompt_runner.pipeline --limit 3")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

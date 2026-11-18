#!/usr/bin/env python3
"""Apply Supabase schema or verify tables exist.

Usage:
  python scripts/apply_schema.py --check-only   # verify tables (default)
  python scripts/apply_schema.py --apply        # apply migration via direct Postgres
  python scripts/apply_schema.py --print-sql    # print SQL editor instructions

For --apply, set SUPABASE_DB_PASSWORD in .env (Supabase Dashboard → Settings → Database).
Alternatively paste supabase/migrations/001_initial_schema.sql into the SQL editor.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MIGRATIONS_DIR = ROOT / "supabase" / "migrations"
MIGRATION_PATH = MIGRATIONS_DIR / "001_initial_schema.sql"
REQUIRED_TABLES = ("prompts", "run_batches", "raw_runs", "brand_config", "scores")


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _project_ref(supabase_url: str) -> str:
    match = re.match(r"https://([^.]+)\.supabase\.co", supabase_url.strip())
    if not match:
        raise ValueError(f"Invalid SUPABASE_URL: {supabase_url}")
    return match.group(1)


def check_tables() -> tuple[list[str], list[str]]:
    from backend.shared.config import get_settings
    from backend.shared.supabase_client import get_supabase_client

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

    client = get_supabase_client(settings)
    present: list[str] = []
    missing: list[str] = []
    for table in REQUIRED_TABLES:
        try:
            client.table(table).select("*", count="exact").limit(1).execute()
            present.append(table)
        except Exception as exc:
            message = str(exc)
            if "PGRST205" in message or "Could not find the table" in message:
                missing.append(table)
            else:
                raise
    return present, missing


def apply_via_postgres(password: str) -> None:
    try:
        import psycopg2
    except ImportError as exc:
        raise SystemExit("psycopg2 not installed. Run: pip install -e '.[db]'") from exc

    from backend.shared.config import get_settings

    settings = get_settings()
    ref = _project_ref(settings.supabase_url)
    migrations = _migration_files()
    if not migrations:
        raise SystemExit(f"No migrations found in {MIGRATIONS_DIR}")
    conn_str = (
        f"host=db.{ref}.supabase.co port=5432 dbname=postgres "
        f"user=postgres password={password} sslmode=require"
    )

    print(f"Applying {len(migrations)} migration(s) to project {ref} ...")
    with psycopg2.connect(conn_str) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for path in migrations:
                print(f"  -> {path.name}")
                cur.execute(path.read_text(encoding="utf-8"))
    print("Migrations applied successfully.")


def print_sql_instructions() -> None:
    from backend.shared.config import get_settings

    settings = get_settings()
    if not settings.supabase_url:
        print("Set SUPABASE_URL in .env first.")
        return

    ref = _project_ref(settings.supabase_url)
    dashboard_url = f"https://supabase.com/dashboard/project/{ref}/sql/new"
    migrations = _migration_files()
    print("=== Apply schema in Supabase SQL Editor ===\n")
    print(f"1. Open: {dashboard_url}")
    print("2. Paste and Run each migration in order:")
    for path in migrations:
        print(f"   - {path}")
    print("3. Verify: python scripts/apply_schema.py --check-only")
    print("4. Seed:    python scripts/seed_supabase.py\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply or verify Supabase schema")
    parser.add_argument("--apply", action="store_true", help="Apply migration via Postgres")
    parser.add_argument("--check-only", action="store_true", help="Only verify tables exist")
    parser.add_argument("--print-sql", action="store_true", help="Print SQL editor instructions")
    args = parser.parse_args()

    if not MIGRATION_PATH.exists():
        print(f"FAIL — migration not found: {MIGRATION_PATH}")
        return 1

    if args.print_sql:
        print_sql_instructions()
        return 0

    try:
        present, missing = check_tables()
    except ValueError as exc:
        print(f"FAIL — {exc}")
        return 1

    if present:
        print(f"OK — tables present: {', '.join(present)}")
    if missing:
        print(f"MISSING — tables not found: {', '.join(missing)}")

    if not missing:
        print("\nSchema is ready.")
        return 0

    if args.apply:
        from backend.shared.config import get_settings

        settings = get_settings()
        if not settings.supabase_db_password:
            print("\nFAIL — SUPABASE_DB_PASSWORD not set in .env")
            print_sql_instructions()
            return 1
        apply_via_postgres(settings.supabase_db_password)
        present, missing = check_tables()
        if missing:
            print(f"FAIL — still missing after apply: {', '.join(missing)}")
            return 1
        print(f"OK — all tables present: {', '.join(present)}")
        return 0

    if not args.check_only:
        print()
        print_sql_instructions()
        print("Or set SUPABASE_DB_PASSWORD in .env and run: python scripts/apply_schema.py --apply")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

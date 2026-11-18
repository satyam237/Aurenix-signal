# Supabase setup

Target project: the one in your `.env` (`SUPABASE_URL`).

## 1. Apply schema

**Option A — SQL Editor (recommended if CLI cannot link the project)**

```bash
python scripts/apply_schema.py --print-sql
```

Open the printed dashboard URL, paste [`migrations/001_initial_schema.sql`](migrations/001_initial_schema.sql), click **Run**.

**Option B — Automated (requires database password)**

Add to `.env`:

```bash
SUPABASE_DB_PASSWORD=your_database_password
```

Password: Supabase Dashboard → **Settings** → **Database** → Database password.

```bash
pip install -e ".[db]"
python scripts/apply_schema.py --apply
```

## 2. Verify schema

```bash
python scripts/apply_schema.py --check-only
```

Expect all five tables: `prompts`, `run_batches`, `raw_runs`, `brand_config`, `scores`.

## 3. Configure `.env`

```bash
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

Use the **service role** key (server-side only). Never expose it in frontend code.

## 4. Seed data

```bash
python scripts/seed_supabase.py
```

Loads 25 prompts + Nautikal truth registry into `prompts` / `brand_config`.

## 5. Verify end-to-end

```bash
python scripts/check_ready.py
python scripts/verify_phase1.py
python -m backend.agents.prompt_runner.pipeline --limit 2
```

Check Supabase Table Editor: `run_batches` and `raw_runs` should have new rows.

## Storage model

| Table | Purpose |
|-------|---------|
| `prompts` | Active prompt library (seeded from JSON) |
| `run_batches` | One row per pipeline/cron execution |
| `raw_runs` | One row per prompt × engine result (text, tokens, cost, status) |
| `brand_config` | Truth registry JSON for brand grounding |
| `scores` | Phase 2 GEO scores (schema ready, unused until judge ships) |

RLS is enabled; only the **service role** key can read/write in MVP.

# Supabase setup (T-04)

## 1. Create project

Create a free Supabase project at [supabase.com](https://supabase.com).

## 2. Apply migration

Run the SQL in [`migrations/001_initial_schema.sql`](migrations/001_initial_schema.sql) via:

- Supabase Dashboard → SQL Editor → paste and run, or
- Supabase CLI: `supabase db push` (after `supabase link`)

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

## 5. Verify

```bash
python scripts/verify_phase1.py
```

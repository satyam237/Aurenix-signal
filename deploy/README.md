# GCP deployment — daily prompt runner (temporary short-term)

Runs `backend.scheduler.cron_runner --force` on a schedule via **Cloud Run Jobs** + **Cloud Scheduler**. This uses the existing Phase 1 pipeline (concurrent runner + brand grounding + Supabase persistence).

## Why not Vertex AI / Model Garden?

Vertex AI has no ongoing free tier for inference. This job calls **OpenAI** and **Gemini APIs** directly (same as local runs). GCP only hosts the cron container.

## Free-tier estimate

| Service | Free allowance | Our usage |
|---------|----------------|-----------|
| Cloud Scheduler | 3 jobs/month free | 1 job (daily) |
| Cloud Run Jobs | ~180k–240k vCPU-sec/month | ~1 run/day × ~5–10 min ≈ 8% of quota |
| Secret Manager | 6 active secret versions | 4 secrets |

Stay within `DAILY_COST_CAP_USD` in `.env` for LLM API spend.

## Prerequisites

1. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
2. `gcloud auth login` and `gcloud config set project YOUR_PROJECT_ID`
3. Billing enabled on the project (required even for free-tier services)
4. Supabase schema applied and seeded locally first (see `supabase/README.md`)

## One-time setup

```bash
cd GEO-Ranker-Signal-15June
chmod +x deploy/gcp_deploy.sh

export GCP_PROJECT_ID=your-gcp-project-id
export GCP_REGION=us-central1

# Create secrets from .env, deploy job, create scheduler
./deploy/gcp_deploy.sh all
```

Or step by step:

```bash
./deploy/gcp_deploy.sh secrets    # Secret Manager: API keys + Supabase
./deploy/gcp_deploy.sh deploy     # Build container from Dockerfile, deploy job
./deploy/gcp_deploy.sh schedule   # Daily 6 AM UTC trigger
./deploy/gcp_deploy.sh run        # Manual test run
```

## Verify after deploy

1. Cloud Console → Cloud Run → Jobs → `aurenix-prompt-runner` → Executions (success)
2. Supabase → `run_batches` (new row) and `raw_runs` (prompt × engine rows)
3. Local: `streamlit run dashboard/health_app.py`

## Customize schedule

```bash
export SCHEDULE="0 6 * * *"   # cron, UTC — default 6 AM UTC
./deploy/gcp_deploy.sh schedule
```

## Troubleshooting

- **Job fails immediately:** Check Cloud Run logs; usually missing secrets or invalid API keys.
- **Empty raw_runs:** Run `python scripts/seed_supabase.py` against the same Supabase project referenced in secrets.
- **Dedup skips all prompts:** `DEDUP_HOURS=6` skips recent successful runs; normal for same-day re-runs.

## Local Docker test (optional)

```bash
docker build -t aurenix-prompt-runner .
docker run --rm --env-file .env aurenix-prompt-runner
```

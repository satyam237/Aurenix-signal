#!/usr/bin/env bash
# Deploy AureniX Signal daily prompt runner to GCP (Cloud Run Jobs + Cloud Scheduler).
# Free-tier friendly: 1 scheduler job (of 3 free), Cloud Run Jobs within monthly vCPU quota.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - GCP project with billing enabled (free tier still requires billing account)
#   - Secret values in environment or .env
#
# Usage:
#   export GCP_PROJECT_ID=your-project-id
#   export GCP_REGION=us-central1
#   ./deploy/gcp_deploy.sh secrets   # one-time: create Secret Manager secrets
#   ./deploy/gcp_deploy.sh deploy    # build + deploy Cloud Run Job
#   ./deploy/gcp_deploy.sh schedule  # create daily 6 AM UTC scheduler
#   ./deploy/gcp_deploy.sh run       # manual test execution
#   ./deploy/gcp_deploy.sh all       # secrets + deploy + schedule

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

JOB_NAME="${JOB_NAME:-aurenix-prompt-runner}"
SCHEDULER_NAME="${SCHEDULER_NAME:-aurenix-prompt-runner-daily}"
SCHEDULE="${SCHEDULE:-0 6 * * *}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-aurenix-cron-runner}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
GCP_REGION="${GCP_REGION:-us-central1}"

die() { echo "ERROR: $*" >&2; exit 1; }

require_gcloud() {
  command -v gcloud >/dev/null 2>&1 || die "gcloud not found. Install: https://cloud.google.com/sdk/docs/install"
}

require_project() {
  [[ -n "$GCP_PROJECT_ID" ]] || die "Set GCP_PROJECT_ID (e.g. export GCP_PROJECT_ID=my-project)"
  gcloud config set project "$GCP_PROJECT_ID" >/dev/null
}

load_env() {
  if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
  fi
}

secret_upsert() {
  local name="$1"
  local value="$2"
  if gcloud secrets describe "$name" --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- --project="$GCP_PROJECT_ID"
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- --replication-policy=automatic --project="$GCP_PROJECT_ID"
  fi
}

cmd_secrets() {
  require_gcloud
  require_project
  load_env
  [[ -n "${OPENAI_API_KEY:-}" ]] || die "OPENAI_API_KEY not set"
  [[ -n "${GEMINI_API_KEY:-}" ]] || die "GEMINI_API_KEY not set"
  [[ -n "${SUPABASE_URL:-}" ]] || die "SUPABASE_URL not set"
  [[ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ]] || die "SUPABASE_SERVICE_ROLE_KEY not set"

  gcloud services enable secretmanager.googleapis.com run.googleapis.com cloudscheduler.googleapis.com --project="$GCP_PROJECT_ID"

  secret_upsert openai-api-key "$OPENAI_API_KEY"
  secret_upsert gemini-api-key "$GEMINI_API_KEY"
  secret_upsert supabase-url "$SUPABASE_URL"
  secret_upsert supabase-service-role-key "$SUPABASE_SERVICE_ROLE_KEY"
  echo "Secrets created/updated in Secret Manager."
}

cmd_deploy() {
  require_gcloud
  require_project

  gcloud run jobs deploy "$JOB_NAME" \
    --source . \
    --region "$GCP_REGION" \
    --project "$GCP_PROJECT_ID" \
    --max-retries 1 \
    --task-timeout 30m \
    --memory 512Mi \
    --cpu 1 \
    --set-secrets "OPENAI_API_KEY=openai-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest" \
    --set-env-vars "BRAND_ID=${BRAND_ID:-nautikal},DAILY_COST_CAP_USD=${DAILY_COST_CAP_USD:-10},DEDUP_HOURS=${DEDUP_HOURS:-6},BULK_CONCURRENCY=${BULK_CONCURRENCY:-6}"

  echo "Cloud Run Job deployed: $JOB_NAME ($GCP_REGION)"
}

cmd_schedule() {
  require_gcloud
  require_project

  local sa_email="${SERVICE_ACCOUNT}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

  if ! gcloud iam service-accounts describe "$sa_email" --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$SERVICE_ACCOUNT" \
      --display-name="AureniX cron runner invoker" \
      --project="$GCP_PROJECT_ID"
  fi

  gcloud run jobs add-iam-policy-binding "$JOB_NAME" \
    --region="$GCP_REGION" \
    --member="serviceAccount:${sa_email}" \
    --role="roles/run.invoker" \
    --project="$GCP_PROJECT_ID"

  local job_uri="https://${GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${GCP_PROJECT_ID}/jobs/${JOB_NAME}:run"

  if gcloud scheduler jobs describe "$SCHEDULER_NAME" --location="$GCP_REGION" --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
    gcloud scheduler jobs update http "$SCHEDULER_NAME" \
      --location="$GCP_REGION" \
      --schedule="$SCHEDULE" \
      --uri="$job_uri" \
      --http-method=POST \
      --oauth-service-account-email="$sa_email" \
      --project="$GCP_PROJECT_ID"
  else
    gcloud scheduler jobs create http "$SCHEDULER_NAME" \
      --location="$GCP_REGION" \
      --schedule="$SCHEDULE" \
      --uri="$job_uri" \
      --http-method=POST \
      --oauth-service-account-email="$sa_email" \
      --project="$GCP_PROJECT_ID"
  fi

  echo "Scheduler configured: $SCHEDULER_NAME ($SCHEDULE UTC)"
}

cmd_run() {
  require_gcloud
  require_project
  gcloud run jobs execute "$JOB_NAME" --region="$GCP_REGION" --project="$GCP_PROJECT_ID" --wait
  echo "Manual job execution finished. Check Supabase run_batches / raw_runs."
}

cmd_all() {
  cmd_secrets
  cmd_deploy
  cmd_schedule
  echo "Done. Run './deploy/gcp_deploy.sh run' to test manually."
}

usage() {
  cat <<EOF
Usage: $0 {secrets|deploy|schedule|run|all}

Environment:
  GCP_PROJECT_ID   (required) Google Cloud project
  GCP_REGION       (default: us-central1)
  JOB_NAME         (default: aurenix-prompt-runner)
  SCHEDULE         (default: 0 6 * * * — daily 6 AM UTC)

Reads API keys from .env when present (for secrets command).
EOF
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    secrets) cmd_secrets ;;
    deploy) cmd_deploy ;;
    schedule) cmd_schedule ;;
    run) cmd_run ;;
    all) cmd_all ;;
    *) usage; exit 1 ;;
  esac
}

main "${1:-}"

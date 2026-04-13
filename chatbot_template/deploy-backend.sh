#!/usr/bin/env bash
# =============================================================================
# Chatbot Template — Manual Backend Deploy
# =============================================================================
# Builds the backend image via Cloud Build and deploys it to Cloud Run.
# The frontend is NOT deployed by this script — Firebase App Hosting watches
# the `chatbot-template` branch on GitHub and auto-deploys on push.
#
# Usage:
#   ./deploy-backend.sh        # uses defaults below
#   PROJECT_ID=foo ./deploy.sh # override project
#
# Branch guard: refuses to run from any branch other than `chatbot-template`.
# This is the production-tracking branch per
# content/reference/INFRASTRUCTURE_CHATBOT_TEMPLATE_REF.md.
# =============================================================================

set -euo pipefail

# ---- Configuration ----------------------------------------------------------
PROJECT_ID="${PROJECT_ID:-chatbot-template-eikasia}"
REGION="${REGION:-us-central1}"
AR_REPO="${AR_REPO:-chatbot-template-app}"
SERVICE="${SERVICE:-chatbot-template-app-backend}"
RUNTIME_SA="${RUNTIME_SA:-chatbot-template-app-sa@${PROJECT_ID}.iam.gserviceaccount.com}"
SECRET_NAME="${SECRET_NAME:-GOOGLE_API_KEY}"
PROD_BRANCH="chatbot-template"

# ---- Branch guard -----------------------------------------------------------
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
if [ "$CURRENT_BRANCH" != "$PROD_BRANCH" ]; then
  echo "ERROR: deploy.sh must be run from the '$PROD_BRANCH' branch." >&2
  echo "       Currently on: $CURRENT_BRANCH" >&2
  echo "       Run: git checkout $PROD_BRANCH" >&2
  exit 1
fi

if ! git diff --quiet HEAD; then
  echo "WARNING: working tree has uncommitted changes." >&2
  read -r -p "Continue anyway? [y/N] " answer
  case "$answer" in
    y|Y) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

SHORT_SHA="$(git rev-parse --short HEAD)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:${SHORT_SHA}"
IMAGE_LATEST="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:latest"

echo "=========================================================="
echo "  Project : $PROJECT_ID"
echo "  Region  : $REGION"
echo "  Service : $SERVICE"
echo "  Image   : $IMAGE"
echo "  SA      : $RUNTIME_SA"
echo "  Branch  : $CURRENT_BRANCH @ $SHORT_SHA"
echo "=========================================================="

# ---- Build via Cloud Build (push happens inside Google's network) -----------
echo ">>> Building backend image via Cloud Build..."
gcloud builds submit ./backend \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --tag="$IMAGE"

# Tag :latest as well
echo ">>> Tagging :latest..."
gcloud artifacts docker tags add "$IMAGE" "$IMAGE_LATEST" \
  --project="$PROJECT_ID" || true

# ---- Deploy to Cloud Run (IAM-only, secret-mounted, WARN logs) --------------
echo ">>> Deploying $SERVICE to Cloud Run..."
gcloud run deploy "$SERVICE" \
  --project="$PROJECT_ID" \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --no-allow-unauthenticated \
  --service-account="$RUNTIME_SA" \
  --set-secrets="GOOGLE_API_KEY=${SECRET_NAME}:latest" \
  --set-env-vars="ALLOWED_ORIGINS=" \
  --min-instances=0 \
  --max-instances=2 \
  --memory=512Mi \
  --cpu=1 \
  --concurrency=80 \
  --labels="app=chatbot-template-app,managed-by=deploy-sh"

# ---- Smoke test -------------------------------------------------------------
echo ">>> Backend deployed. Smoke testing /health (requires gcloud auth)..."
URL="$(gcloud run services describe "$SERVICE" \
  --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')"
TOKEN="$(gcloud auth print-identity-token)"
curl -fsS -H "Authorization: Bearer $TOKEN" "$URL/health" && echo
echo ">>> Done. Service URL: $URL"

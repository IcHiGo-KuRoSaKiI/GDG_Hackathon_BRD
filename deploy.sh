#!/usr/bin/env bash
set -euo pipefail

# ============================================
# BRD Generator — Deploy Backend to Cloud Run
# ============================================
# Usage: ./deploy.sh [image-tag]
#
# Prerequisites:
#   - gcloud CLI authenticated (gcloud auth login)
#   - Terraform installed
#   - infra/terraform.tfvars populated

# Ensure gcloud is in PATH
export PATH="${HOME}/google-cloud-sdk/bin:${PATH}"

# Authenticate Terraform with the service account key
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export GOOGLE_APPLICATION_CREDENTIALS="${SCRIPT_DIR}/service-account-key.json"

PROJECT_ID="gdg-brd-generator-2026"
REGION="us-central1"
REPO_NAME="brd-generator"
IMAGE_NAME="backend"
IMAGE_TAG="${1:-latest}"

FULL_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "=== Step 1: Ensure Artifact Registry repo exists ==="

cd infra
terraform init -upgrade
terraform apply -target=google_artifact_registry_repository.backend -auto-approve
cd ..

echo ""
echo "=== Step 2: Build and push Docker image via Cloud Build ==="
echo "Image: ${FULL_IMAGE}"
echo ""

gcloud builds submit \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --tag="${FULL_IMAGE}" \
  --timeout=600s \
  .

echo ""
echo "=== Step 3: Deploy Cloud Run service ==="

cd infra
terraform apply -var="image_tag=${IMAGE_TAG}" -auto-approve

echo ""
echo "=== Deployment complete ==="
terraform output cloud_run_url

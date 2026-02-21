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

PROJECT_ID="gdg-brd-generator-2026"
REGION="us-central1"
REPO_NAME="brd-generator"
IMAGE_NAME="backend"
IMAGE_TAG="${1:-latest}"

FULL_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "=== Step 1: Build and push Docker image via Cloud Build ==="
echo "Image: ${FULL_IMAGE}"
echo ""

gcloud builds submit \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --tag="${FULL_IMAGE}" \
  --timeout=600s \
  .

echo ""
echo "=== Step 2: Terraform apply ==="

cd infra
terraform init -upgrade
terraform apply -var="image_tag=${IMAGE_TAG}" -auto-approve

echo ""
echo "=== Deployment complete ==="
terraform output cloud_run_url

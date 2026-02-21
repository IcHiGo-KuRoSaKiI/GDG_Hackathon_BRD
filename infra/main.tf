terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# Artifact Registry — Docker image repository
# ---------------------------------------------------------------------------
resource "google_artifact_registry_repository" "backend" {
  location      = var.region
  repository_id = "brd-generator"
  description   = "Docker images for BRD Generator backend"
  format        = "DOCKER"
}

# ---------------------------------------------------------------------------
# Cloud Run v2 Service
# ---------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "backend" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    timeout = "300s"

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}/backend:${var.image_tag}"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "STORAGE_BUCKET"
        value = var.storage_bucket
      }
      env {
        name  = "GEMINI_API_KEY"
        value = var.gemini_api_key
      }
      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }
      env {
        name  = "GEMINI_MAX_OUTPUT_TOKENS"
        value = "16384"
      }
      env {
        name  = "JWT_SECRET_KEY"
        value = var.jwt_secret_key
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "ALLOWED_ORIGINS"
        value = var.allowed_origins
      }
      # GOOGLE_APPLICATION_CREDENTIALS intentionally omitted — ADC via service account
    }
  }

  depends_on = [google_artifact_registry_repository.backend]
}

# ---------------------------------------------------------------------------
# IAM — Allow unauthenticated access (API has its own JWT auth layer)
# ---------------------------------------------------------------------------
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = google_cloud_run_v2_service.backend.project
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

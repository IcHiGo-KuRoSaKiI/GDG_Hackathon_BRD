variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "brd-generator-api"
}

variable "image_tag" {
  description = "Docker image tag (set by deploy script)"
  type        = string
  default     = "latest"
}

variable "service_account_email" {
  description = "Service account email for Cloud Run"
  type        = string
}

variable "gemini_api_key" {
  description = "Gemini API key"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "storage_bucket" {
  description = "GCS bucket name"
  type        = string
  default     = "gdg-brd-generator-files"
}

variable "allowed_origins" {
  description = "Comma-separated CORS origins"
  type        = string
  default     = "http://localhost:3000"
}

variable "gemini_model" {
  description = "Gemini model name"
  type        = string
  default     = "gemini-2.5-pro"
}

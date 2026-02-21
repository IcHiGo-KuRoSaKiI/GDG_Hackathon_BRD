"""
Configuration settings for BRD Generator backend.
Loads environment variables and provides app-wide settings.
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Firebase Configuration
    google_application_credentials: str
    google_cloud_project: str
    storage_bucket: str

    # Gemini AI Configuration
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_temperature: float = 0.2
    gemini_max_retries: int = 3

    # Server Configuration
    port: int = 8080
    environment: str = "development"
    allowed_origins: List[str] = ["http://localhost:3000"]

    # Processing Configuration
    max_file_size_mb: int = 50
    chunk_size: int = 1000  # Words per chunk for citations
    chunk_overlap: int = 100  # Words overlap between chunks

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

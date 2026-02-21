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
    google_application_credentials: str = ""  # Empty = use ADC (Cloud Run)
    google_cloud_project: str
    storage_bucket: str

    # Gemini AI Configuration
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-pro"
    gemini_temperature: float = 0.2
    gemini_max_retries: int = 3

    # Gemini Token Limits (generous for structured outputs)
    # Context: 1M total, Input: 131k max, Output: 64k max
    # Note: Structured outputs can hit MAX_TOKENS bug, use higher limits
    gemini_max_input_tokens: int = 100000   # Under free tier 125k limit
    gemini_max_output_tokens: int = 16384   # Higher limit to prevent truncation

    # JWT Authentication Configuration
    jwt_secret_key: str = "your-secret-key-change-in-production"  # Override in .env
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Server Configuration
    port: int = 8080
    environment: str = "development"
    allowed_origins: str = "http://localhost:3000"  # Comma-separated string

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed_origins into list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # Processing Configuration
    max_file_size_mb: int = 50
    chunk_size: int = 1000  # Words per chunk for citations
    chunk_overlap: int = 100  # Words overlap between chunks

    # RAG / Embedding Configuration
    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768  # text-embedding-004 output dimensions
    rag_top_k: int = 20  # Chunks to retrieve per query
    rag_similarity_threshold: float = 0.3  # Minimum cosine similarity
    rag_max_iterations: int = 5  # Max Gemini loop iterations (down from 30)

    class Config:
        # Look for .env in project root (parent of backend/)
        import os
        from pathlib import Path
        backend_dir = Path(__file__).parent.parent
        project_root = backend_dir.parent
        env_file = str(project_root / ".env")
        case_sensitive = False


# Global settings instance
settings = Settings()

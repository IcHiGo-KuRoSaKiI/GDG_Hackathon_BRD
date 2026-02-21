"""
Project data models.
Represents a project container for documents and BRDs.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    """Request model for creating a new project."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class Project(BaseModel):
    """Complete project model with metadata."""
    project_id: str
    user_id: str  # Owner of this project
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    brd_count: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProjectResponse(BaseModel):
    """API response model for project operations."""
    project_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    document_count: int = 0
    brd_count: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

"""
Deletion models for two-step delete functionality.

Supports preview → confirm pattern with background processing.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class DeleteScope(str, Enum):
    """Scope of deletion operation."""
    DOCUMENT = "document"
    PROJECT = "project"


class DeleteStatus(str, Enum):
    """Status of deletion job."""
    PENDING = "pending"          # Preview created, awaiting confirmation
    QUEUED = "queued"            # Confirmed, waiting to start
    DELETING = "deleting"        # Active deletion in progress
    COMPLETE = "complete"        # Successfully completed
    FAILED = "failed"            # Failed with errors
    CANCELLED = "cancelled"      # User cancelled before execution


class DeletePreview(BaseModel):
    """Preview of what will be deleted."""
    deletion_id: str = Field(..., description="Unique deletion job ID")
    scope: DeleteScope = Field(..., description="Document or project deletion")
    project_id: str = Field(..., description="Project ID")
    project_name: str = Field(..., description="Project name for display")
    doc_id: Optional[str] = Field(None, description="Document ID (for document scope)")
    filename: Optional[str] = Field(None, description="Document filename (for document scope)")

    # Counts
    documents_to_delete: int = Field(..., description="Number of documents to delete")
    chunks_to_delete: int = Field(..., description="Total chunks to delete")
    brds_to_delete: int = Field(..., description="Number of BRDs to delete")
    storage_files_to_delete: int = Field(..., description="Number of storage files to delete")

    # Timing
    estimated_time_seconds: int = Field(..., description="Estimated deletion time")
    created_at: str = Field(..., description="Preview creation timestamp (ISO 8601)")
    expires_at: str = Field(..., description="Preview expiration timestamp (ISO 8601)")

    @field_validator('expires_at', mode='before')
    @classmethod
    def set_expiration(cls, v, info):
        """Set expiration to 5 minutes from creation if not provided."""
        if v is None and 'created_at' in info.data:
            created = datetime.fromisoformat(info.data['created_at'])
            return (created + timedelta(minutes=5)).isoformat()
        return v

    @field_validator('estimated_time_seconds', mode='before')
    @classmethod
    def estimate_time(cls, v, info):
        """Estimate deletion time based on counts if not provided."""
        if v is None:
            # Rough estimates:
            # - 100 chunks/second
            # - 10 storage files/second
            # - 1 second base overhead
            chunks = info.data.get('chunks_to_delete', 0)
            files = info.data.get('storage_files_to_delete', 0)
            return max(1, (chunks // 100) + (files // 10) + 1)
        return v


class DeletionProgress(BaseModel):
    """Progress tracking for active deletion."""
    chunks_deleted: int = Field(0, description="Number of chunks deleted so far")
    chunks_total: int = Field(0, description="Total chunks to delete")
    storage_files_deleted: int = Field(0, description="Storage files deleted so far")
    storage_files_total: int = Field(0, description="Total storage files to delete")
    documents_deleted: int = Field(0, description="Documents deleted so far")
    documents_total: int = Field(0, description="Total documents to delete")
    brds_deleted: int = Field(0, description="BRDs deleted so far")
    brds_total: int = Field(0, description="Total BRDs to delete")
    current_step: str = Field("initializing", description="Current deletion step")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore storage."""
        return {
            "chunks_deleted": self.chunks_deleted,
            "chunks_total": self.chunks_total,
            "storage_files_deleted": self.storage_files_deleted,
            "storage_files_total": self.storage_files_total,
            "documents_deleted": self.documents_deleted,
            "documents_total": self.documents_total,
            "brds_deleted": self.brds_deleted,
            "brds_total": self.brds_total,
            "current_step": self.current_step
        }


class DeleteJob(BaseModel):
    """Complete deletion job record."""
    deletion_id: str = Field(..., description="Unique deletion job ID")
    user_id: str = Field(..., description="User who initiated deletion")
    scope: DeleteScope = Field(..., description="Document or project deletion")
    status: DeleteStatus = Field(DeleteStatus.PENDING, description="Current status")

    # References
    project_id: str = Field(..., description="Project ID")
    doc_id: Optional[str] = Field(None, description="Document ID (for document scope)")

    # Preview data
    preview: DeletePreview = Field(..., description="Original preview data")

    # Progress tracking
    progress: Optional[DeletionProgress] = Field(None, description="Current progress")

    # Timing
    created_at: str = Field(..., description="Job creation timestamp (ISO 8601)")
    started_at: Optional[str] = Field(None, description="Deletion start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")

    # Error tracking
    errors: List[str] = Field(default_factory=list, description="Non-critical errors encountered")
    error_message: Optional[str] = Field(None, description="Critical error message (if failed)")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore storage."""
        data = {
            "deletion_id": self.deletion_id,
            "user_id": self.user_id,
            "scope": self.scope.value,
            "status": self.status.value,
            "project_id": self.project_id,
            "preview": self.preview.dict(),
            "created_at": self.created_at,
            "errors": self.errors
        }

        if self.doc_id:
            data["doc_id"] = self.doc_id
        if self.progress:
            data["progress"] = self.progress.to_dict()
        if self.started_at:
            data["started_at"] = self.started_at
        if self.completed_at:
            data["completed_at"] = self.completed_at
        if self.error_message:
            data["error_message"] = self.error_message

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeleteJob":
        """Create DeleteJob from Firestore document."""
        # Convert enum strings to enums
        data["scope"] = DeleteScope(data["scope"])
        data["status"] = DeleteStatus(data["status"])

        # Convert nested models
        data["preview"] = DeletePreview(**data["preview"])
        if "progress" in data and data["progress"]:
            data["progress"] = DeletionProgress(**data["progress"])

        return cls(**data)


class DeleteConfirmRequest(BaseModel):
    """Request to confirm and execute deletion."""
    deletion_id: str = Field(..., description="Deletion job ID from preview")
    confirmation: str = Field(..., description="Must be exactly 'DELETE'")

    @field_validator('confirmation')
    @classmethod
    def validate_confirmation(cls, v):
        """Ensure user typed DELETE exactly."""
        if v != "DELETE":
            raise ValueError("Confirmation must be exactly 'DELETE'")
        return v


class DeleteResponse(BaseModel):
    """Response after confirming deletion (202 Accepted)."""
    status: str = Field(..., description="Current status (typically 'deleting')")
    deletion_id: str = Field(..., description="Deletion job ID for polling")
    message: str = Field(..., description="Human-readable message")
    note: Optional[str] = Field(None, description="Additional instructions for client")
